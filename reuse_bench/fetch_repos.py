"""Check out every benchmark repository at its pinned commit (see data/repos.json).

    python -m reuse_bench.fetch_repos [--manifest data/repos.json] [--dest data/repos]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=Path("data/repos.json"))
    parser.add_argument("--dest", type=Path, default=Path("data/repos"))
    args = parser.parse_args(argv)

    for name, spec in json.loads(args.manifest.read_text()).items():
        repo = args.dest / name
        if not (repo / ".git").exists():
            repo.mkdir(parents=True, exist_ok=True)
            git("init", "-q", cwd=repo)
            git("remote", "add", "origin", spec["url"], cwd=repo)
        head = subprocess.run(["git", "rev-parse", "-q", "--verify", "HEAD"], cwd=repo,
                              capture_output=True, text=True).stdout.strip()
        if head != spec["commit"]:
            git("fetch", "-q", "--depth", "1", "origin", spec["commit"], cwd=repo)
            git("checkout", "-q", "--force", spec["commit"], cwd=repo)
        print(f"{name}: {git('rev-parse', '--short', 'HEAD', cwd=repo)}")


if __name__ == "__main__":
    main()
