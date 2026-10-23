"""Aggregate metrics.jsonl into a markdown table per model x condition x instruction.

    python -m reuse_bench.summarize results/<run>/metrics.jsonl [--out results/<run>/summary.md]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def rate(rows: list[dict], key) -> str:
    return f"{100 * sum(bool(key(r)) for r in rows) / len(rows):.0f}%"


def summarize(rows: list[dict]) -> str:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["model"], r["condition"], r["instruction"])].append(r)
    out = ["| model | condition | instruction | n | applied | tests pass | reuses helper | "
           "reuse & pass | helper in context | new helper defined |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for (model, condition, instruction), rs in sorted(groups.items()):
        out.append(" | ".join([
            f"| {model.split('/')[-1]}", condition, instruction, str(len(rs)),
            rate(rs, lambda r: r["applied"]), rate(rs, lambda r: r["tests_pass"]),
            rate(rs, lambda r: r["reuse_helper"]),
            rate(rs, lambda r: r["reuse_helper"] and r["tests_pass"]),
            rate(rs, lambda r: r["helper_in_context"]),
            rate(rs, lambda r: r.get("new_functions")),
        ]) + " |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    table = summarize([json.loads(line) for line in args.metrics.read_text().splitlines() if line.strip()])
    print(table)
    if args.out:
        args.out.write_text(table)


if __name__ == "__main__":
    main()
