"""Compute every number in the paper from results/ and write LaTeX table bodies to paper/tables/.

    .venv/bin/python paper/make_tables.py
"""
import json
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "tables"
MODELS = [("Q2.5C-7B", "qwen7b-v1"), ("DSC-6.7B", "deepseek67b-v1"),
          ("Q3C-30B", "qwen3coder30b-v1"), ("Q3.8-27B", "qwen38-27b-v1")]
RENAMED = [("Q3C-30B", "qwen3coder30b-v1", "qwen3coder30b-renamed"),
           ("Q3.8-27B", "qwen38-27b-v1", "qwen38-27b-renamed")]
CONDS = ["none", "bm25", "oracle", "file"]


def load(run):
    return {(r["task_id"], r["condition"], r["instruction"]): r
            for r in map(json.loads, (ROOT / "results" / run / "metrics.jsonl").open())}


def valid(r):
    return bool(r["tests_pass"] and r.get("compliant"))


def mcnemar(a, b):
    """Exact two-sided McNemar test on discordant counts."""
    m = a + b
    return min(1.0, 2 * sum(comb(m, i) for i in range(min(a, b) + 1)) / 2 ** m) if m else 1.0


def discordant(x, y, keys, f=lambda r: r["reuse_helper"]):
    return sum(f(x[k]) and not f(y[k]) for k in keys), sum(f(y[k]) and not f(x[k]) for k in keys)


def fmt_p(p):
    return "<.001" if p < 0.001 else f"{p:.3f}".lstrip("0") if p < 0.995 else "1.0"


def rows(M, cond, ins):
    return [r for k, r in M.items() if k[1] == cond and k[2] == ins]


def pct(n, d):
    return f"{100 * n / d:.0f}"


def main():
    OUT.mkdir(exist_ok=True)
    data = {run: load(run) for _, run in MODELS}
    stats = {}

    # Table 1: reuse (valid) per model x instruction x condition
    lines = []
    for name, run in MODELS:
        M = data[run]
        for ins in ("generic", "reuse"):
            cells = []
            for c in CONDS:
                rs = rows(M, c, ins)
                cells.append(f"{pct(sum(r['reuse_helper'] for r in rs), len(rs))} "
                             f"\\small({pct(sum(valid(r) for r in rs), len(rs))})")
            label = name if ins == "generic" else ""
            lines.append(f"{label} & {ins} & " + " & ".join(cells) + r" \\")
        lines.append(r"\midrule" if run != MODELS[-1][1] else "")
    (OUT / "main.tex").write_text("\n".join(lines) + "\n")

    # Table 2: funnel with the helper guaranteed in context (oracle) and with BM25
    lines = []
    for name, run in MODELS:
        M = data[run]
        cells = []
        for c in ("bm25", "oracle"):
            for ins in ("generic", "reuse"):
                rs = rows(M, c, ins)
                in_ctx = [r for r in rs if r["helper_in_context"]]
                called = [r for r in in_ctx if r["reuse_helper"]]
                broken = sum(not r["tests_pass"] for r in called)
                cells.append(f"{len(rs) - len(in_ctx)}/{len(in_ctx) - len(called)}/{broken}/{len(called) - broken}")
        lines.append(f"{name} & " + " & ".join(cells) + r" \\")
    (OUT / "funnel.tex").write_text("\n".join(lines) + "\n")

    # Table 3: position ablation
    lines = []
    for name, run in MODELS:
        M = data[run]
        cells = []
        for ins in ("generic", "reuse"):
            keys = [k for k in M if k[1] == "oracle_first" and k[2] == ins]
            n = {pos: sum(M[(k[0], pos, ins)]["reuse_helper"] for k in keys)
                 for pos in ("oracle_first", "oracle", "oracle_last")}
            first = {k[0]: M[(k[0], "oracle_first", ins)]["reuse_helper"] for k in keys}
            last = {k[0]: M[(k[0], "oracle_last", ins)]["reuse_helper"] for k in keys}
            a = sum(first[t] and not last[t] for t in first)
            b = sum(last[t] and not first[t] for t in first)
            cells += [str(n["oracle_first"]), str(n["oracle"]), str(n["oracle_last"]), f"{a}/{b}", fmt_p(mcnemar(a, b))]
        lines.append(f"{name} & " + " & ".join(cells) + r" \\")
    (OUT / "position.tex").write_text("\n".join(lines) + "\n")

    # Table 4: renaming check
    lines = []
    for name, orig, ren in RENAMED:
        O, R = load(orig), load(ren)
        for ins in ("generic", "reuse"):
            cells = []
            for c in ("bm25", "oracle", "file"):
                keys = [k for k in R if k[1] == c and k[2] == ins]
                lost, gained = discordant(O, R, keys)
                cells.append(f"{sum(O[k]['reuse_helper'] for k in keys)}$\\to${sum(R[k]['reuse_helper'] for k in keys)}"
                             f"\\,\\small({fmt_p(mcnemar(lost, gained))})")
            label = name if ins == "generic" else ""
            lines.append(f"{label} & {ins} & " + " & ".join(cells) + r" \\")
        stats[f"{ren}_memorised"] = sum(r["uses_original_name"] for r in R.values())
        stats[f"{ren}_n"] = len(R)
        lines.append(r"\midrule" if ren != RENAMED[-1][2] else "")
    (OUT / "renamed.tex").write_text("\n".join(lines) + "\n")

    # Pairwise model comparisons quoted in the text
    q7, q3c, q38 = data["qwen7b-v1"], data["qwen3coder30b-v1"], data["qwen38-27b-v1"]
    for c in CONDS + ["oracle_first"]:
        for ins in ("generic", "reuse"):
            keys = [k for k in q38 if k[1] == c and k[2] == ins]
            for other, M in (("q3c", q3c), ("q7", q7)):
                a, b = discordant(q38, M, keys)
                stats[f"q38_vs_{other}_{c}_{ins}"] = f"{a} vs {b}, p={fmt_p(mcnemar(a, b))}"
            a, b = discordant(q3c, q7, keys)
            stats[f"q3c_vs_q7_{c}_{ins}"] = f"{a} vs {b}, p={fmt_p(mcnemar(a, b))}"
    R38, R3c = load("qwen38-27b-renamed"), load("qwen3coder30b-renamed")
    for c in ("bm25", "oracle", "file"):
        for ins in ("generic", "reuse"):
            keys = [k for k in R38 if k[1] == c and k[2] == ins]
            a, b = discordant(R38, R3c, keys)
            stats[f"renamed_q38_vs_q3c_{c}_{ins}"] = f"{a} vs {b}, p={fmt_p(mcnemar(a, b))}"
    for name, run in MODELS:
        M = data[run]
        stats[f"{run}_valid_range"] = [pct(sum(valid(r) for r in rows(M, c, i)), 129) for c in CONDS for i in ("generic", "reuse")]
        stats[f"{run}_new_helper_none"] = pct(sum(bool(r.get("new_functions")) for r in rows(M, "none", "generic") + rows(M, "none", "reuse")), 258)
        bm = rows(M, "bm25", "generic")
        stats["bm25_recall"] = pct(sum(r["helper_in_context"] for r in bm), len(bm))
        stats["bm25_mrr"] = f"{sum(1 / r['helper_rank'] for r in bm if r['helper_rank']) / len(bm):.2f}"
    (OUT / "stats.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
