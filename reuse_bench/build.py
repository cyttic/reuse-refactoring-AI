"""Build reuse-refactoring tasks from a Python repository.

    python -m reuse_bench.build data/repos/<repo> --out data/tasks/<repo>.jsonl
"""
from __future__ import annotations

import argparse
import difflib
import json
import shlex
import subprocess
from collections import Counter
from pathlib import Path

from .index import RepoIndex
from .inline import Limits, Mutation, Rejected, find_sites, inline
from .validate import Sandbox


def _git_commit(repo: Path) -> str | None:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True)
    return proc.stdout.strip() or None


def make_task(repo: Path, commit: str | None, mutation: Mutation, usages: Counter[str]) -> dict:
    site = mutation.site
    rel = site.module.path.as_posix()
    helper_origin = f"{site.helper_module.name}.{site.helper_qualname}"
    patch = "".join(difflib.unified_diff(
        site.module.source.splitlines(keepends=True), mutation.new_source.splitlines(keepends=True),
        fromfile=f"a/{rel}", tofile=f"b/{rel}"))
    return {
        "id": f"{repo.name}::{site.module.name}.{site.caller_qualname}::{helper_origin}",
        "source": "injected",
        "repo": repo.name,
        "commit": commit,
        "caller_file": rel,
        "caller_qualname": site.caller_qualname,
        "caller_line": site.caller.lineno,
        "call_line": site.stmt.lineno,
        "call_kind": site.kind,
        "call_style": site.style,
        "helper_file": site.helper_module.path.as_posix(),
        "helper_qualname": helper_origin,
        "helper_same_module": site.helper_module is site.module,
        "helper_usages_elsewhere": usages[helper_origin] - 1,
        "helper_lines": site.helper.end_lineno - site.helper.lineno + 1,
        "inlined_code": mutation.inlined,
        "task_patch": patch,   # applying it to `commit` produces the task state
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pytest-args", help="default: the repo's entry in --manifest")
    parser.add_argument("--manifest", type=Path, default=Path("data/repos.json"))
    parser.add_argument("--timeout", type=int, default=900, help="seconds per test-suite run")
    parser.add_argument("--max-tasks", type=int)
    parser.add_argument("--max-per-helper", type=int, default=3)
    parser.add_argument("--min-helper-size", type=int, default=Limits.min_helper_size)
    parser.add_argument("--max-helper-lines", type=int, default=Limits.max_helper_lines)
    parser.add_argument("--no-validate", action="store_true", help="skip running the test suite")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    if args.pytest_args is None:
        manifest = json.loads(args.manifest.read_text()) if args.manifest.exists() else {}
        args.pytest_args = manifest.get(repo.name, {}).get("pytest_args", "-x -q -p no:cacheprovider")
    index = RepoIndex.build(repo)
    limits = Limits(args.min_helper_size, args.max_helper_lines)
    usages = index.usage_counts()
    reasons: Counter[str] = Counter()
    per_helper: Counter[str] = Counter()
    used_callers: set[tuple[str, str]] = set()
    candidates: list[tuple[Mutation, dict]] = []

    for site in find_sites(index):
        caller_key = (site.module.name, site.caller_qualname)
        helper_origin = f"{site.helper_module.name}.{site.helper_qualname}"
        if caller_key in used_callers:
            reasons["caller already has a task"] += 1
            continue
        if per_helper[helper_origin] >= args.max_per_helper:
            reasons["helper quota reached"] += 1
            continue
        try:
            mutation = inline(index, site, limits)
        except Rejected as exc:
            reasons[str(exc)] += 1
            continue
        used_callers.add(caller_key)
        per_helper[helper_origin] += 1
        candidates.append((mutation, make_task(repo, _git_commit(repo), mutation, usages)))

    tasks = [task for _, task in candidates]
    if not args.no_validate and candidates:
        tasks = []
        with Sandbox(repo, shlex.split(args.pytest_args), args.timeout) as sandbox:
            first_module = candidates[0][0].site.module.name
            if not sandbox.imports_from_sandbox(first_module):
                raise SystemExit(f"tests would not import {first_module} from the sandbox; "
                                 "check the package layout or uninstall the installed copy")
            baseline, executed = sandbox.baseline_coverage()
            if not baseline.passed:
                raise SystemExit(f"baseline test suite fails:\n{baseline.output}")
            print(f"baseline suite passed in {baseline.seconds:.1f}s")
            for mutation, task in candidates:
                covered = task["call_line"] in executed.get(task["caller_file"], set())
                if not covered:
                    reasons["call site not covered by tests"] += 1
                    continue
                result = sandbox.check(mutation.site.module.path, mutation.new_source)
                if not result.passed:
                    reasons["tests fail after inlining"] += 1
                    continue
                task["validation"] = {"tests_pass": True, "call_site_covered": True,
                                      "test_seconds": round(result.seconds, 2)}
                tasks.append(task)
                print(f"  ok  {task['id']}")
                if args.max_tasks and len(tasks) >= args.max_tasks:
                    break
    elif args.max_tasks:
        tasks = tasks[: args.max_tasks]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for task in tasks:
            fh.write(json.dumps(task) + "\n")

    print(f"\n{len(index.modules)} modules indexed, {len(candidates)} candidates, {len(tasks)} tasks -> {args.out}")
    for reason, count in reasons.most_common():
        print(f"  {count:5d}  {reason}")


if __name__ == "__main__":
    main()
