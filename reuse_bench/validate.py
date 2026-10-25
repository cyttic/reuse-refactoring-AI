"""Run a repository's pytest suite on a sandbox copy, with and without a mutation."""
from __future__ import annotations

import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

# Address-space cap for each test run: a generated edit that builds an infinite list (e.g. list() over
# zip_longest(seq, repeat(x))) then fails with MemoryError instead of exhausting the machine's RAM,
# which had the kernel kill the whole evaluation on the GPU server.
MEMORY_LIMIT = 4 * 1024 ** 3


def _limit_memory() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))


IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".venv", "venv", ".tox", ".nox",
                                ".pytest_cache", ".mypy_cache", "*.pyc")


@dataclass
class TestResult:
    passed: bool
    seconds: float
    output: str     # tail of stdout/stderr, for debugging rejected tasks


class Sandbox:
    """A throwaway copy of the repository; tests import the package from this copy."""

    def __init__(self, repo: Path, pytest_args: list[str], timeout: int):
        self.repo = repo.resolve()
        self.pytest_args = pytest_args
        self.timeout = timeout

    def __enter__(self) -> Sandbox:
        self._tmp = tempfile.mkdtemp(prefix="reuse-bench-")
        self.root = Path(self._tmp) / self.repo.name
        shutil.copytree(self.repo, self.root, ignore=IGNORE)
        return self

    def __exit__(self, *exc) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        paths = [str(p) for p in (self.root / "src", self.root) if p.is_dir()]
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env

    def _run(self, cmd: list[str]) -> TestResult:
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=self.root, env=self._env(), capture_output=True,
                                  text=True, timeout=self.timeout, preexec_fn=_limit_memory)
        except subprocess.TimeoutExpired:
            return TestResult(False, time.monotonic() - start, "timeout")
        output = (proc.stdout + proc.stderr)[-2000:]
        return TestResult(proc.returncode == 0, time.monotonic() - start, output)

    def imports_from_sandbox(self, module: str) -> bool:
        """Guard against tests silently importing an installed copy of the package."""
        code = f"import importlib; print(importlib.import_module({module!r}).__file__)"
        proc = subprocess.run([sys.executable, "-c", code], cwd=self.root, env=self._env(),
                              capture_output=True, text=True, timeout=120)
        lines = proc.stdout.strip().splitlines()
        return proc.returncode == 0 and bool(lines) and \
            Path(lines[-1]).resolve().is_relative_to(self.root.resolve())

    def baseline_coverage(self) -> tuple[TestResult, dict[str, set[int]]]:
        """Run the unmodified suite under coverage; return executed lines per repo-relative file."""
        data, report = Path(self._tmp) / ".coverage", Path(self._tmp) / "coverage.json"
        # An empty rcfile: the repository's own coverage config may need plugins we do not install.
        rcfile = Path(self._tmp) / "coveragerc"
        rcfile.write_text("[run]\n")
        result = self._run([sys.executable, "-m", "coverage", "run", f"--rcfile={rcfile}",
                            f"--data-file={data}", "-m", "pytest", *self.pytest_args])
        executed: dict[str, set[int]] = {}
        if result.passed:
            subprocess.run([sys.executable, "-m", "coverage", "json", f"--rcfile={rcfile}",
                            f"--data-file={data}", "-o", str(report)],
                           cwd=self.root, capture_output=True, timeout=300)
            if report.exists():
                for name, info in json.loads(report.read_text())["files"].items():
                    path = (self.root / name).resolve()
                    if path.is_relative_to(self.root.resolve()):
                        executed[str(path.relative_to(self.root.resolve()))] = set(info["executed_lines"])
        return result, executed

    def check(self, rel_path: Path, new_source: str) -> TestResult:
        """Run the suite with one file replaced, then restore it."""
        target = self.root / rel_path
        original = target.read_text(encoding="utf-8")
        target.write_text(new_source, encoding="utf-8")
        try:
            return self._run([sys.executable, "-m", "pytest", *self.pytest_args])
        finally:
            target.write_text(original, encoding="utf-8")
