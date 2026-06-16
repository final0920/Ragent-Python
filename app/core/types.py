"""检索相关共享类型（跨 infra/core/graph 复用，避免循环依赖）。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievedChunk:
    id: str
    content: str
    score: float = 0.0
    source: str = ""          # vector | bm25 | fused | reranked
    metadata: dict = field(default_factory=dict)  # collection_name/doc_id/chunk_index
