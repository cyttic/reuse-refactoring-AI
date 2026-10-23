"""Index the modules, top-level functions and global name bindings of a Python repository."""
from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = {".git", ".hg", ".venv", "venv", "env", ".tox", ".nox", "build", "dist",
             "__pycache__", "docs", "doc", "examples", "benchmarks", "site-packages"}
TEST_DIRS = {"tests", "test", "testing"}


@dataclass
class Module:
    name: str                 # dotted name, e.g. "pkg.utils"
    path: Path                # relative to the repository root
    source: str
    tree: ast.Module
    is_package: bool
    # global name -> origin ("pkg.utils.helper", "os.path", ...)
    bindings: dict[str, str] = field(default_factory=dict)
    functions: dict[str, ast.FunctionDef] = field(default_factory=dict)


def is_test_path(rel: Path) -> bool:
    return (any(part in TEST_DIRS for part in rel.parts[:-1])
            or rel.name.startswith("test_") or rel.name.endswith("_test.py")
            or rel.name == "conftest.py")


def module_name(rel: Path) -> tuple[str, bool]:
    parts = list(rel.with_suffix("").parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts = parts[:-1]
    if parts and parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts), is_package


def _relative_base(module: Module, level: int) -> str:
    package = module.name.split(".") if module.is_package else module.name.split(".")[:-1]
    if level > 1:
        package = package[: len(package) - (level - 1)]
    return ".".join(package)


def collect_bindings(module: Module) -> None:
    """Record what every top-level name refers to; nested or conditional imports are ignored."""
    for node in module.tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    module.bindings[alias.asname] = alias.name
                else:
                    top = alias.name.split(".")[0]
                    module.bindings[top] = top
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = ".".join(p for p in (_relative_base(module, node.level), node.module) if p)
            for alias in node.names:
                if alias.name != "*":
                    module.bindings[alias.asname or alias.name] = f"{base}.{alias.name}"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module.bindings[node.name] = f"{module.name}.{node.name}"
            if isinstance(node, ast.FunctionDef):
                module.functions[node.name] = node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for name in ast.walk(target):
                    if isinstance(name, ast.Name):
                        module.bindings[name.id] = f"{module.name}.{name.id}"


class RepoIndex:
    def __init__(self, root: Path, modules: dict[str, Module]):
        self.root = root
        self.modules = modules

    @classmethod
    def build(cls, root: Path) -> RepoIndex:
        root = root.resolve()
        modules: dict[str, Module] = {}
        for path in sorted(root.rglob("*.py")):
            rel = path.relative_to(root)
            if any(part in SKIP_DIRS or part.startswith(".") for part in rel.parts[:-1]):
                continue
            if is_test_path(rel) or rel.name == "setup.py":
                continue
            name, is_package = module_name(rel)
            if not name:
                continue
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError, ValueError):
                continue
            module = Module(name, rel, source, tree, is_package)
            collect_bindings(module)
            modules[name] = module
        return cls(root, modules)

    def resolve(self, origin: str | None) -> str | None:
        """Follow re-exports (e.g. `from .utils import f` in __init__) to the defining module."""
        seen = set()
        while origin and origin not in seen:
            seen.add(origin)
            mod, _, name = origin.rpartition(".")
            module = self.modules.get(mod)
            if module is None or name not in module.bindings:
                return origin
            origin = module.bindings[name]
        return origin

    def function(self, origin: str | None) -> tuple[Module, ast.FunctionDef] | None:
        origin = self.resolve(origin)
        if not origin:
            return None
        mod, _, name = origin.rpartition(".")
        module = self.modules.get(mod)
        if module is None or name not in module.functions:
            return None
        return module, module.functions[name]

    def usage_counts(self) -> Counter[str]:
        """How many times each resolved origin is referenced by name across the repository."""
        counts: Counter[str] = Counter()
        for module in self.modules.values():
            for node in ast.walk(module.tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in module.bindings:
                    counts[self.resolve(module.bindings[node.id])] += 1
        return counts
