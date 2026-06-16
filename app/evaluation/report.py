"""report 阶段：由 scores.json 生成 report.md + per_sample.csv；compare 对比两次评分。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.evaluation.score import METRIC_NAMES


def report(scores_path: str, out_dir: str) -> None:
    scores = json.loads(Path(scores_path).read_text(encoding="utf-8"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    overall = scores.get("overall", {})
    lines = ["# RAGAS 评测报告", "", f"样本 {scores.get('samples')} ｜ ragas-n {scores.get('ragas_n')}", "", "## 总体指标", "", "| 指标 | 分数 |", "|---|---|"]
    for m in METRIC_NAMES:
        if m in overall:
            lines.append(f"| {m} | {overall[m]} |")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    per = scores.get("per_sample", [])
    if per:
        cols = ["query"] + [m for m in METRIC_NAMES if any(m in r for r in per)]
        with open(out / "per_sample.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in per:
                w.writerow({c: r.get(c, "") for c in cols})
    print(f"报告 -> {out / 'report.md'}, {out / 'per_sample.csv'}")


def compare(a_path: str, b_path: str) -> None:
    a = json.loads(Path(a_path).read_text(encoding="utf-8")).get("overall", {})
    b = json.loads(Path(b_path).read_text(encoding="utf-8")).get("overall", {})
    print(f"{'指标':<22}{'A':>10}{'B':>10}{'Δ(B-A)':>12}")
    for m in METRIC_NAMES:
        if m in a or m in b:
            av, bv = a.get(m, 0.0), b.get(m, 0.0)
            print(f"{m:<22}{av:>10.4f}{bv:>10.4f}{bv - av:>+12.4f}")
