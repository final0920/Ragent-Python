"""P4 多轮记忆：滑动窗口 + 增量摘要压缩（水位线 last_message_id 防重复压缩）。"""

from __future__ import annotations

from sqlalchemy import select

from app.config import settings
from app.infra import clients
from app.models import ConversationSummary, Message
from app.utils import gen_id


async def _ordered_messages(session, conversation_id: str) -> list[Message]:
    rows = (
        await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.deleted.is_(False))
            .order_by(Message.create_time.asc(), Message.id.asc())
        )
    ).scalars().all()
    return list(rows)


async def _get_summary(session, conversation_id: str) -> ConversationSummary | None:
    return (
        await session.execute(
            select(ConversationSummary)
            .where(
                ConversationSummary.conversation_id == conversation_id,
                ConversationSummary.deleted.is_(False),
            )
            .order_by(ConversationSummary.create_time.desc())
            .limit(1)
        )
    ).scalars().first()


async def load_memory(session, conversation_id: str, keep_turns: int) -> tuple[str, list[dict]]:
    """返回 (摘要文本, 最近历史)。历史取最近 keep_turns*2 条且以 user 起头。"""
    summary = await _get_summary(session, conversation_id)
    summary_text = summary.content if summary else ""

    all_msgs = await _ordered_messages(session, conversation_id)
    recent = all_msgs[-(keep_turns * 2):] if keep_turns > 0 else all_msgs
    history = [{"role": m.role, "content": m.content} for m in recent]
    while history and history[0]["role"] != "user":
        history.pop(0)
    return summary_text, history


async def maybe_summarize(session, conversation_id: str) -> None:
    """超过阈值时，把"旧窗口外"的消息增量压缩进摘要。"""
    if not settings.rag_summary_enabled:
        return
    keep = settings.rag_history_keep_turns
    all_msgs = await _ordered_messages(session, conversation_id)
    turns = len(all_msgs) // 2
    if turns < settings.rag_summary_start_turns:
        return

    summary = await _get_summary(session, conversation_id)
    watermark = summary.last_message_id if summary else ""

    # 待压缩 = 最近 keep*2 条之前、且在水位线之后的消息
    older = all_msgs[: -(keep * 2)] if keep > 0 else []
    if watermark:
        idx = next((i for i, m in enumerate(older) if m.id == watermark), -1)
        older = older[idx + 1:] if idx >= 0 else older
    if not older:
        return

    convo = "\n".join(f"{m.role}: {m.content}" for m in older)
    prompt = [
        {"role": "system", "content": f"将对话压缩成不超过{settings.rag_summary_max_chars}字的中文摘要，保留关键事实/结论/用户偏好。"},
        {"role": "user", "content": (f"已有摘要：{summary.content}\n\n" if summary and summary.content else "") + f"新增对话：\n{convo}"},
    ]
    try:
        new_summary = (await clients.chat(prompt))[: settings.rag_summary_max_chars]
    except Exception:
        return
    if not new_summary:
        return

    last_id = older[-1].id
    if summary:
        summary.content = new_summary
        summary.last_message_id = last_id
    else:
        session.add(
            ConversationSummary(
                id=gen_id(), conversation_id=conversation_id,
                content=new_summary, last_message_id=last_id,
            )
        )
    await session.commit()
