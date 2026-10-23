"""Select a balanced, reproducible subset of validated tasks into data/tasks/<repo>.jsonl.

    python -m reuse_bench.select_tasks build/*.jsonl --per-repo 12 --out-dir data/tasks

Cross-module tasks (helper in another module, where retrieval matters most) are always kept;
the rest of each repository's quota is a seeded random sample of same-module tasks.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("built", type=Path, nargs="+", help="validated task files from reuse_bench.build")
    parser.add_argument("--per-repo", type=int, default=12)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out-dir", type=Path, default=Path("data/tasks"))
    args = parser.parse_args(argv)

    by_repo: dict[str, list[dict]] = defaultdict(list)
    for path in args.built:
        for line in path.read_text().splitlines():
            task = json.loads(line)
            if task.get("validation", {}).get("tests_pass"):
                by_repo[task["repo"]].append(task)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    total = Counter()
    for repo in sorted(by_repo):
        tasks = sorted(by_repo[repo], key=lambda t: t["id"])
        cross = [t for t in tasks if not t["helper_same_module"]]
        same = [t for t in tasks if t["helper_same_module"]]
        random.Random(f"{args.seed}:{repo}").shuffle(same)
        chosen = sorted(cross + same[: max(0, args.per_repo - len(cross))], key=lambda t: t["id"])
        (args.out_dir / f"{repo}.jsonl").write_text("".join(json.dumps(t) + "\n" for t in chosen))
        total.update(tasks=len(chosen), cross=sum(not t["helper_same_module"] for t in chosen))
        print(f"{repo:16} {len(chosen):3} of {len(tasks):3} validated "
              f"({sum(not t['helper_same_module'] for t in chosen)} cross-module)")
    print(f"total: {total['tasks']} tasks, {total['cross']} cross-module")


if __name__ == "__main__":
    main()
