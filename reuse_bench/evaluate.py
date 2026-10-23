"""CPU stage: apply each generated refactoring, run the repository tests and measure reuse.

    python -m reuse_bench.evaluate --tasks data/tasks/*.jsonl --generations results/<run>/generations.jsonl \
        --out results/<run>/metrics.jsonl
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import shlex
from collections import defaultdict
from pathlib import Path

from .edit import EditError, apply_edit
from .index import Module, RepoIndex, collect_bindings
from .patching import apply_patch
from .prompting import find_function, load_tasks
from .validate import Sandbox


def called_origins(index: RepoIndex, module_name: str, source: str, qualname: str) -> set[str]:
    """Resolved targets of all calls made inside the function (e.g. 'pkg.utils.helper')."""
    tree = ast.parse(source)
    module = Module(module_name, Path(), source, tree, False)
    collect_bindings(module)
    origins = set()
    for node in ast.walk(find_function(tree, qualname)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in module.bindings:
            origins.add(index.resolve(module.bindings[func.id]))
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) \
                and func.value.id in module.bindings:
            origins.add(index.resolve(f"{index.resolve(module.bindings[func.value.id])}.{func.attr}"))
    return origins


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasks", type=Path, nargs="+", required=True)
    parser.add_argument("--generations", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repos-dir", type=Path, default=Path("data/repos"))
    parser.add_argument("--manifest", type=Path, default=Path("data/repos.json"))
    parser.add_argument("--timeout", type=int, default=300, help="seconds per test-suite run")
    args = parser.parse_args(argv)

    tasks = {t["id"]: t for t in load_tasks(args.tasks)}
    manifest = json.loads(args.manifest.read_text())
    done = set()
    if args.out.exists():
        done = {(r["task_id"], r["condition"], r["instruction"], r["model"])
                for r in map(json.loads, args.out.read_text().splitlines())}
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for gen in map(json.loads, args.generations.read_text().splitlines()):
        if (gen["task_id"], gen["condition"], gen["instruction"], gen["model"]) not in done:
            by_repo[tasks[gen["task_id"]]["repo"]].append(gen)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    for repo, gens in by_repo.items():
        repo_root = args.repos_dir / repo
        index = RepoIndex.build(repo_root)
        pytest_args = shlex.split(manifest[repo]["pytest_args"])
        print(f"{repo}: evaluating {len(gens)} generations")
        with Sandbox(repo_root, pytest_args, args.timeout) as sandbox, args.out.open("a") as fh:
            for gen in gens:
                task = tasks[gen["task_id"]]
                original = (repo_root / task["caller_file"]).read_text(encoding="utf-8")
                mutated = apply_patch(original, task["task_patch"])
                module_name = next(m.name for m in index.modules.values()
                                   if m.path.as_posix() == task["caller_file"])
                record = {k: gen[k] for k in ("task_id", "condition", "instruction", "model",
                                              "helper_in_context", "helper_rank", "file_truncated")}
                record.update(repo=repo, helper_same_module=task["helper_same_module"])
                try:
                    new_source, info = apply_edit(mutated, task["caller_qualname"], gen["output"])
                except EditError as exc:
                    record.update(applied=False, error=str(exc), tests_pass=False, reuse_helper=False)
                else:
                    calls = called_origins(index, module_name, new_source, task["caller_qualname"])
                    result = sandbox.check(Path(task["caller_file"]), new_source)
                    diff = "".join(difflib.unified_diff(
                        mutated.splitlines(keepends=True), new_source.splitlines(keepends=True),
                        fromfile=f"a/{task['caller_file']}", tofile=f"b/{task['caller_file']}"))
                    record.update(
                        applied=True, error=None, **info, diff=diff,
                        tests_pass=result.passed,
                        reuse_helper=task["helper_qualname"] in calls,
                        repo_calls=sorted(c for c in calls if index.function(c) is not None),
                        unchanged=new_source == mutated,
                    )
                fh.write(json.dumps(record) + "\n")
                fh.flush()
                status = "pass" if record["tests_pass"] else "FAIL"
                print(f"  {status} reuse={record['reuse_helper']!s:5} {gen['condition']:6} "
                      f"{gen['instruction']:7} {gen['task_id']}")


if __name__ == "__main__":
    main()
