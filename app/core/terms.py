"""词典归一化:按 query_term_mapping 把同义/口语词替换为标准词(最长优先,幂等)。"""

from __future__ import annotations

from sqlalchemy import select

from app.models import QueryTermMapping


async def normalize(session, text: str) -> str:
    if not text:
        return text
    rows = (
        await session.execute(
            select(QueryTermMapping).where(
                QueryTermMapping.enabled.is_(True), QueryTermMapping.deleted.is_(False)
            ).order_by(QueryTermMapping.priority)
        )
    ).scalars().all()
    # 最长 source 优先,避免短词先替换破坏长词
    out = text
    for r in sorted(rows, key=lambda x: -len(x.source_term)):
        if r.source_term and r.source_term in out:
            out = out.replace(r.source_term, r.target_term)
    return out
