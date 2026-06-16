"""LangGraph 主图：load_memory → retrieve → build_prompt，随后流式生成。

非流式准备用 LangGraph 编排；最终 LLM 逐字流式在图外进行（MVP 简化）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.config import settings
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
    history: list[dict]
    chunks: list[RetrievedChunk]
    messages: list[dict]


async def _resolve_collection(session, collection: str | None) -> str | None:
    if collection:
        return collection
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
    session, cid = state["session"], state["conversation_id"]
    keep = settings.rag_history_keep_turns * 2
    rows = (
        await session.execute(
            select(Message.role, Message.content)
            .where(Message.conversation_id == cid, Message.deleted.is_(False))
            .order_by(Message.create_time.desc())
            .limit(keep)
        )
    ).all()
    history = [{"role": r.role, "content": r.content} for r in reversed(rows)]
    # 保证以 user 起头
    while history and history[0]["role"] != "user":
        history.pop(0)
    return {"history": history}


async def _retrieve(state: ChatState) -> ChatState:
    collection = await _resolve_collection(state["session"], state.get("collection"))
    if not collection:
        return {"chunks": []}
    try:
        chunks = await retrieve_mod.retrieve(
            state["session"],
            state["question"],
            collection,
            dense_topk=settings.rag_dense_topk,
            sparse_topk=settings.rag_sparse_topk,
            rrf_k=settings.rag_rrf_k,
            rerank_topn=settings.rag_rerank_topn,
        )
    except Exception:
        chunks = []
    return {"chunks": chunks}


async def _build_prompt(state: ChatState) -> ChatState:
    chunks = state.get("chunks") or []
    ctx = "\n\n".join(f"[{i + 1}] {c.content}" for i, c in enumerate(chunks))
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if ctx:
        messages.append({"role": "system", "content": f"【知识库内容】\n{ctx}"})
    messages.extend(state.get("history") or [])
    messages.append({"role": "user", "content": state["question"]})
    return {"messages": messages}


def build_graph():
    g = StateGraph(ChatState)
    g.add_node("load_memory", _load_memory)
    g.add_node("retrieve", _retrieve)
    g.add_node("build_prompt", _build_prompt)
    g.add_edge(START, "load_memory")
    g.add_edge("load_memory", "retrieve")
    g.add_edge("retrieve", "build_prompt")
    g.add_edge("build_prompt", END)
    return g.compile()


_GRAPH = build_graph()


async def stream_chat(
    session, conversation_id: str, question: str, collection: str | None = None
) -> AsyncIterator[dict]:
    """yield SSE 事件：meta / message(response) / finish / done。"""
    # 确保会话存在 + 持久化 user 消息
    await _ensure_conversation(session, conversation_id)
    session.add(Message(id=gen_id(), conversation_id=conversation_id, role="user", content=question))
    await session.commit()

    state = await _GRAPH.ainvoke(
        {"session": session, "conversation_id": conversation_id, "question": question, "collection": collection}
    )
    yield {"event": "meta", "data": {"conversationId": conversation_id, "chunks": len(state.get("chunks") or [])}}

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
