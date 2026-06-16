"""评估集定义与读写。一条样本含问题、标准答案、意图、是否应走检索。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "eval_set.json"


@dataclass
class EvalSample:
    id: str
    query: str
    ground_truth: str = ""
    intent_l1: str = ""
    intent_l2: str = ""
    requires_rag: bool = True
    collection: str = ""              # 留空则用默认 KB
    expected_doc_ids: list[str] = field(default_factory=list)


# 种子样本（演示用，少量；实际建议扩到 100+ 覆盖各意图）。
SEED: list[dict] = [
    {"id": "q1", "query": "什么是RAG？它解决什么问题？", "ground_truth": "RAG 即检索增强生成，先从知识库检索相关片段再交给大模型生成，解决上下文窗口限制与检索精度问题，降低幻觉与成本。", "intent_l1": "基础概念", "intent_l2": "RAG定义", "requires_rag": True},
    {"id": "q2", "query": "为什么要做文档分块？chunkSize 怎么定？", "ground_truth": "整篇文档粒度太粗无法精准检索，需分块；chunkSize 常见 200~1000 字符、问答场景偏小，overlap 取其 10%~25% 防止边界信息被切断。", "intent_l1": "数据处理", "intent_l2": "分块", "requires_rag": True},
    {"id": "q3", "query": "混合检索里 RRF 是怎么融合的？为什么不用分数加权？", "ground_truth": "RRF 按各路排名计算 1/(k+rank) 求和(k=60)，只看排名不看分数，规避不同检索分数量纲不一致、归一化敏感的问题。", "intent_l1": "检索", "intent_l2": "融合", "requires_rag": True},
    {"id": "q4", "query": "今天天气怎么样？", "ground_truth": "该问题与知识库无关，应礼貌说明无法回答或转其它渠道。", "intent_l1": "闲聊", "intent_l2": "越界", "requires_rag": False},
]


def write_seed(path: Path = DEFAULT_PATH) -> int:
    path.write_text(json.dumps(SEED, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(SEED)


def load_eval_set(path: Path = DEFAULT_PATH) -> list[EvalSample]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [EvalSample(**d) for d in data]


def sample_to_dict(s: EvalSample) -> dict:
    return asdict(s)
