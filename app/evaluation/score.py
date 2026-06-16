"""score 阶段：用 RAGAS 五指标评分（ragas 惰性导入；judge LLM/embeddings 走本地 OpenAI 兼容端点）。

多轮取均值压方差（--ragas-n）。输出 {overall, per_sample} 到 scores.json。
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from app.config import settings

METRIC_NAMES = ["faithfulness", "answer_relevancy", "answer_correctness", "context_precision", "context_recall"]


def _build_judges():
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper

    llm = LangchainLLMWrapper(
        ChatOpenAI(
            model=settings.llm_chat_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "ollama",
            temperature=0.0,
        )
    )
    emb = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(
            model=settings.embedding_model,
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key or "ollama",
            check_embedding_ctx_length=False,
        )
    )
    return llm, emb


def score(run_path: str, out_path: str, ragas_n: int = 1) -> dict:
    from ragas import EvaluationDataset, evaluate
    from ragas.metrics import (
        answer_correctness,
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    results = json.loads(Path(run_path).read_text(encoding="utf-8"))
    rows = [
        {
            "user_input": r["query"],
            "response": r["answer"],
            "retrieved_contexts": r["contexts"] or [""],
            "reference": r["ground_truth"] or r["answer"],
        }
        for r in results
    ]
    dataset = EvaluationDataset.from_list(rows)
    llm, emb = _build_judges()
    metrics = [faithfulness, answer_relevancy, answer_correctness, context_precision, context_recall]

    per_run_overall: list[dict] = []
    last_df = None
    for i in range(max(1, ragas_n)):
        res = evaluate(dataset, metrics=metrics, llm=llm, embeddings=emb)
        df = res.to_pandas()
        last_df = df
        per_run_overall.append({m: _safe_mean(df, m) for m in METRIC_NAMES if m in df.columns})
        print(f"  [score] run {i + 1}/{ragas_n} done")

    overall = {
        m: round(statistics.mean([r[m] for r in per_run_overall if m in r]), 4)
        for m in METRIC_NAMES
        if any(m in r for r in per_run_overall)
    }
    per_sample = []
    if last_df is not None:
        for _, row in last_df.iterrows():
            per_sample.append(
                {"query": str(row.get("user_input", ""))[:80]}
                | {m: _round(row.get(m)) for m in METRIC_NAMES if m in last_df.columns}
            )

    out = {"overall": overall, "ragas_n": ragas_n, "samples": len(rows), "per_sample": per_sample}
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"评分完成 -> {out_path}\n  overall: {overall}")
    return out


def _safe_mean(df, col: str) -> float:
    vals = [v for v in df[col].tolist() if v is not None and v == v]  # 过滤 NaN
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _round(v):
    try:
        return round(float(v), 4) if v == v else None
    except (TypeError, ValueError):
        return None
