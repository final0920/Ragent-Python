"""LangGraph 主图：load_memory → resolve_intents → retrieve → build_prompt，随后流式生成。

P4 记忆摘要：load_memory 取摘要+滑窗历史，生成后增量压缩。
P5 意图：resolve_intents LLM 打分，分数驱动定向/全局检索。
最终 LLM 逐字流式在图外进行（MVP 简化）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.config import settings
from app.core import intent as intent_mod
from app.core import memory as memory_mod
from app.core import retrieve as retrieve_mod
from app.core.types import RetrievedChunk
from app.infra import clients
from app.models import Conversation, KnowledgeBase, Message
from app.utils import gen_id

SYSTEM_PROMPT = (
    "你是企业知识库智能客服。仅依据提供的【知识库内容】回答；"
    "若内容不足以回答，明确说不确定，不要编造。回答简洁、可引用编号。"
)


class ChatState(TypedDict, total=False):
    session: Any
    conversation_id: str
    question: str
    collection: str | None
    summary: str
    history: list[dict]
    intents: list[dict]
    collections: list[str]
    use_global: bool
    chunks: list[RetrievedChunk]
    messages: list[dict]


async def _default_collection(session) -> str | None:
    row = (
        await session.execute(
            select(KnowledgeBase.collection_name)
            .where(KnowledgeBase.deleted.is_(False))
            .order_by(KnowledgeBase.create_time.desc())
            .limit(1)
        )
    ).first()
    return row[0] if row else None


async def _load_memory(state: ChatState) -> ChatState:
    summary, history = await memory_mod.load_memory(
        state["session"], state["conversation_id"], settings.rag_history_keep_turns
    )
    return {"summary": summary, "history": history}


async def _resolve_intents(state: ChatState) -> ChatState:
    try:
        r = await intent_mod.route(state["session"], state["question"])
    except Exception:
        r = {"intents": [], "collections": [], "use_global": True}
    return {"intents": r["intents"], "collections": r["collections"], "use_global": r["use_global"]}


async def _retrieve_one(session, query: str, collection: str) -> list[RetrievedChunk]:
    try:
        return await retrieve_mod.retrieve(
            session, query, collection,
            dense_topk=settings.rag_dense_topk,
            sparse_topk=settings.rag_sparse_topk,
            rrf_k=settings.rag_rrf_k,
            rerank_topn=settings.rag_rerank_topn,
        )
    except Exception:
        return []


async def _retrieve(state: ChatState) -> ChatState:
    session, query = state["session"], state["question"]
    # 显式指定 > 意图定向 > 全局默认
    if state.get("collection"):
        targets = [state["collection"]]
    elif state.get("collections"):
        targets = state["collections"]
    else:
        default = await _default_collection(session)
        targets = [default] if default else []

    if not targets:
        return {"chunks": []}

    merged: dict[str, RetrievedChunk] = {}
    for col in targets:
        for c in await _retrieve_one(session, query, col):
            cur = merged.get(c.id)
            if cur is None or c.score > cur.score:
                merged[c.id] = c
    chunks = sorted(merged.values(), key=lambda c: -c.score)[: settings.rag_rerank_topn]
    return {"chunks": chunks}


async def _build_prompt(state: ChatState) -> ChatState:
    chunks = state.get("chunks") or []
    ctx = "\n\n".join(f"[{i + 1}] {c.content}" for i, c in enumerate(chunks))
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if ctx:
        messages.append({"role": "system", "content": f"【知识库内容】\n{ctx}"})
    if state.get("summary"):
        messages.append({"role": "system", "content": f"【历史摘要】\n{state['summary']}"})
    messages.extend(state.get("history") or [])
    messages.append({"role": "user", "content": state["question"]})
    return {"messages": messages}


def build_graph():
    g = StateGraph(ChatState)
    g.add_node("load_memory", _load_memory)
    g.add_node("resolve_intents", _resolve_intents)
    g.add_node("retrieve", _retrieve)
    g.add_node("build_prompt", _build_prompt)
    g.add_edge(START, "load_memory")
    g.add_edge("load_memory", "resolve_intents")
    g.add_edge("resolve_intents", "retrieve")
    g.add_edge("retrieve", "build_prompt")
    g.add_edge("build_prompt", END)
    return g.compile()


_GRAPH = build_graph()


async def stream_chat(
    session, conversation_id: str, question: str, collection: str | None = None
) -> AsyncIterator[dict]:
    """yield SSE 事件：meta / message(response|think) / finish / done。"""
    await _ensure_conversation(session, conversation_id)
    session.add(Message(id=gen_id(), conversation_id=conversation_id, role="user", content=question))
    await session.commit()

    state = await _GRAPH.ainvoke(
        {"session": session, "conversation_id": conversation_id, "question": question, "collection": collection}
    )
    yield {
        "event": "meta",
        "data": {
            "conversationId": conversation_id,
            "chunks": len(state.get("chunks") or []),
            "intents": state.get("intents") or [],
        },
    }

    answer_parts: list[str] = []
    async for ev in clients.chat_stream(state["messages"]):
        if ev["type"] == "response":
            answer_parts.append(ev["content"])
            yield {"event": "message", "data": {"type": "response", "content": ev["content"]}}
        elif ev["type"] == "think":
            yield {"event": "message", "data": {"type": "think", "content": ev["content"]}}

    answer = "".join(answer_parts)
    session.add(Message(id=gen_id(), conversation_id=conversation_id, role="assistant", content=answer))
    await session.commit()

    # P4：生成后增量压缩记忆
    try:
        await memory_mod.maybe_summarize(session, conversation_id)
    except Exception:
        pass

    yield {"event": "finish", "data": {"length": len(answer)}}
    yield {"event": "done", "data": {}}


async def _ensure_conversation(session, conversation_id: str) -> None:
    exists = (
        await session.execute(
            select(Conversation.id).where(Conversation.conversation_id == conversation_id).limit(1)
        )
    ).first()
    if not exists:
        session.add(Conversation(id=gen_id(), conversation_id=conversation_id, title=""))
        await session.commit()
