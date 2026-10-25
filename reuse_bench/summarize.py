"""Aggregate metrics.jsonl into markdown tables per model x condition x instruction.

    python -m reuse_bench.summarize results/<run>/metrics.jsonl [--out results/<run>/summary.md]

Tables: overall rates; the reuse funnel (helper in context -> helper called -> tests pass) with
each failure attributed to the stage where it happened; retrieval quality of the helper.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def pct(num: int, den: int) -> str:
    return f"{100 * num / den:.0f}% ({num}/{den})" if den else "–"


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in rows]) + "\n"


def summarize(rows: list[dict]) -> str:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["model"].split("/")[-1], r["condition"], r["instruction"])].append(r)
    keys = sorted(groups)

    overall = []
    funnel = []
    for key in keys:
        rs = groups[key]
        n = len(rs)
        reused = [r for r in rs if r["reuse_helper"]]
        valid = [r for r in rs if r["tests_pass"] and r.get("compliant")]
        overall.append([*key, str(n),
                        pct(sum(r["applied"] for r in rs), n),
                        pct(sum(r["tests_pass"] for r in rs), n),
                        pct(sum(bool(r.get("compliant")) for r in rs), n),
                        pct(len(valid), n),
                        pct(len(reused), n),
                        pct(sum(bool(r.get("reuse_any")) for r in rs), n),
                        pct(sum(bool(r["reuse_helper"]) for r in valid), n),
                        pct(sum(bool(r.get("new_functions")) for r in rs), n),
                        pct(sum(bool(r.get("hallucinated_imports")) for r in rs), n)])
        in_ctx = [r for r in rs if r["helper_in_context"]]
        called = [r for r in in_ctx if r["reuse_helper"]]
        funnel.append([*key,
                       pct(len(in_ctx), n),
                       pct(len(called), len(in_ctx)),
                       pct(sum(r["tests_pass"] for r in called), len(called)),
                       # where the successes were lost, as shares of all n tasks
                       str(n - len(in_ctx)),
                       str(len(in_ctx) - len(called)),
                       str(sum(bool(r.get("reuse_any")) for r in in_ctx if not r["reuse_helper"])),
                       str(len(called) - sum(r["tests_pass"] for r in called)),
                       str(sum(r["reuse_helper"] for r in rs if not r["helper_in_context"]))])

    retrieval = []
    for key in keys:
        rs = [r for r in groups[key] if r["condition"] == "bm25"]
        if rs:
            ranks = [r["helper_rank"] for r in rs]
            retrieval.append([*key, str(len(rs)),
                              pct(sum(rk is not None for rk in ranks), len(rs)),
                              f"{sum(1 / rk for rk in ranks if rk) / len(rs):.2f}"])

    renamed = []
    for key in keys:
        rs = [r for r in groups[key] if r.get("renamed")]
        if rs:
            renamed.append([*key, str(len(rs)),
                            pct(sum(r["reuse_helper"] for r in rs), len(rs)),
                            pct(sum(r["uses_original_name"] for r in rs), len(rs))])

    out = ["## Overall\n",
           "*compliant*: signature kept and no existing code redefined (violations are dropped before "
           "testing); *valid*: tests pass and compliant; *reuses any*: calls the target helper or another "
           "repository function the input did not call (check these by hand).\n",
           table(["model", "condition", "instruction", "n", "applied", "tests pass", "compliant", "valid",
                  "reuses helper", "reuses any", "valid & reuses helper", "defines new helper",
                  "hallucinated import"], overall),
           "\n## Reuse funnel\n",
           "Stages: helper in context → helper called (given in context) → tests pass (given called). "
           "Loss columns count tasks lost at each stage; the last column counts reuse without the "
           "helper in context (e.g. from training data).\n",
           table(["model", "condition", "instruction", "helper in context", "called (of in context)",
                  "pass (of called)", "lost: not in context", "lost: ignored", "…of which reused another fn",
                  "lost: broken",
                  "called without context"], funnel)]
    if retrieval:
        out += ["\n## Retrieval of the helper (BM25)\n",
                table(["model", "condition", "instruction", "n", "recall@k", "MRR"], retrieval)]
    if renamed:
        out += ["\n## Contamination check: helper renamed in the prompt\n",
                "*uses original name*: the output names the helper as in the real repository although "
                "the prompt only showed the neutral name, i.e. from memory (counted as not reusing).\n",
                table(["model", "condition", "instruction", "n", "reuses helper (shown name)",
                       "uses original name"], renamed)]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    text = summarize([json.loads(line) for line in args.metrics.read_text().splitlines() if line.strip()])
    print(text)
    if args.out:
        args.out.write_text(text)


if __name__ == "__main__":
    main()
