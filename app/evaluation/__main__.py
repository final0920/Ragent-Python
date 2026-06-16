"""评测 CLI：
  uv run python -m app.evaluation init                          # 写种子评估集
  uv run python -m app.evaluation run   --out runs/run.json     # 录制(需在线服务)
  uv run python -m app.evaluation score --run runs/run.json --out runs/scores.json [--ragas-n 3]   # 需 uv sync --group eval
  uv run python -m app.evaluation report --scores runs/scores.json --out-dir runs/report
  uv run python -m app.evaluation compare --a runs/base.json --b runs/opt.json
"""

from __future__ import annotations

import argparse
import asyncio


def main() -> None:
    p = argparse.ArgumentParser(prog="app.evaluation")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    pr = sub.add_parser("run")
    pr.add_argument("--out", default="runs/run.json")

    ps = sub.add_parser("score")
    ps.add_argument("--run", default="runs/run.json")
    ps.add_argument("--out", default="runs/scores.json")
    ps.add_argument("--ragas-n", type=int, default=1)

    prp = sub.add_parser("report")
    prp.add_argument("--scores", default="runs/scores.json")
    prp.add_argument("--out-dir", default="runs/report")

    pc = sub.add_parser("compare")
    pc.add_argument("--a", required=True)
    pc.add_argument("--b", required=True)

    args = p.parse_args()

    if args.cmd == "init":
        from app.evaluation.dataset import write_seed

        print(f"写入种子评估集 {write_seed()} 条")
    elif args.cmd == "run":
        from pathlib import Path

        from app.evaluation.runner import record

        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(record(args.out))
    elif args.cmd == "score":
        from pathlib import Path

        from app.evaluation.score import score

        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        score(args.run, args.out, ragas_n=args.ragas_n)
    elif args.cmd == "report":
        from app.evaluation.report import report

        report(args.scores, args.out_dir)
    elif args.cmd == "compare":
        from app.evaluation.report import compare

        compare(args.a, args.b)


if __name__ == "__main__":
    main()
