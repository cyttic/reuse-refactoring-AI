"""Build the refactoring prompt for one task under one condition and instruction variant.

All retrieval conditions share the same base context (the module's imports plus the target
function) and differ only in the snippets added to it, so the helper reaches the model only
through retrieval. `file` shows the whole module instead, as a realistic reference.
"""
from __future__ import annotations

import ast
import json
import random
from pathlib import Path

from .index import RepoIndex
from .patching import apply_patch
from .retrieval import BM25, Snippet, repo_snippets, tokenize

SYSTEM = "You are an expert Python developer working in an existing code base."

INSTRUCTIONS = {
    "generic": "Refactor this function to improve its readability and maintainability.",
    "reuse": ("Refactor this function to improve its readability and maintainability. "
              "Where possible, reuse existing functions from the project instead of "
              "re-implementing their logic."),
}
# none = C0, bm25 = C1, oracle = C4 (helper among k-1 BM25 distractors); dense (C2) and agentic (C3) come later
CONDITIONS = ("none", "bm25", "oracle", "file")


def load_tasks(paths: list[Path]) -> list[dict]:
    return [json.loads(line) for p in paths for line in p.read_text().splitlines() if line.strip()]


def find_function(tree: ast.Module, qualname: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    cls_name, _, name = qualname.rpartition(".")
    body = tree.body
    if cls_name:
        body = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name).body
    return next(n for n in body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)


class TaskContext:
    """A task resolved against its repository checkout: mutated file, snippets and retriever."""

    def __init__(self, task: dict, repo_root: Path, index: RepoIndex):
        self.task = task
        original = (repo_root / task["caller_file"]).read_text(encoding="utf-8")
        self.mutated = apply_patch(original, task["task_patch"])
        self.tree = ast.parse(self.mutated)
        self.function = find_function(self.tree, task["caller_qualname"])
        self.lines = self.mutated.splitlines(keepends=True)
        self.function_source = "".join(self.lines[self.function.lineno - 1: self.function.end_lineno])
        module = next(m.name for m in index.modules.values() if m.path.as_posix() == task["caller_file"])
        # Retrieval corpus: every repository function except the target itself, whose original
        # version (still calling the helper) is what the index holds.
        target = f"{module}.{task['caller_qualname']}"
        self.snippets = [s for s in repo_snippets(index) if s.origin != target]
        self._bm25: BM25 | None = None

    def _ranking(self) -> list[int]:
        if self._bm25 is None:
            self._bm25 = BM25([tokenize(s.source) for s in self.snippets])
        return self._bm25.top(tokenize(self.function_source), len(self.snippets))

    def retrieve(self, k: int) -> list[Snippet]:
        return [self.snippets[i] for i in self._ranking()[:k]]

    def oracle(self, k: int) -> list[Snippet]:
        """The helper plus the top k-1 BM25 distractors, at a fixed per-task random position."""
        helper = next(s for s in self.snippets if s.origin == self.task["helper_qualname"])
        others = [self.snippets[i] for i in self._ranking() if self.snippets[i] is not helper][: k - 1]
        others.insert(random.Random(self.task["id"]).randint(0, len(others)), helper)
        return others

    def function_view(self) -> str:
        """The module's top-level imports and the target function (with its class header)."""
        imports = "".join("".join(self.lines[n.lineno - 1: n.end_lineno])
                          for n in self.tree.body if isinstance(n, (ast.Import, ast.ImportFrom)))
        parts = [imports] if imports else []
        if "." in self.task["caller_qualname"]:
            cls = next(n for n in self.tree.body
                       if isinstance(n, ast.ClassDef) and n.name == self.task["caller_qualname"].split(".")[0])
            header = "".join(self.lines[cls.lineno - 1: cls.body[0].lineno - 1]).rstrip()
            parts.append(f"{header}\n    ...\n\n{self.function_source}")
        else:
            parts.append(self.function_source)
        return "\n# ...\n\n".join(p.rstrip("\n") + "\n" for p in parts)

    def file_view(self, max_chars: int) -> tuple[str, bool]:
        """The mutated file, or a window around the target function if the file is too long."""
        if len(self.mutated) <= max_chars:
            return self.mutated, False
        margin = 400
        while margin > 0:
            start = max(0, self.function.lineno - 1 - margin)
            end = min(len(self.lines), self.function.end_lineno + margin)
            view = "".join(self.lines[start:end])
            if len(view) <= max_chars:
                break
            margin //= 2
        head = "# ... (earlier lines omitted) ...\n" if start > 0 else ""
        tail = "# ... (later lines omitted) ...\n" if end < len(self.lines) else ""
        return head + view + tail, True


def build_prompt(ctx: TaskContext, condition: str, instruction: str, k: int, max_file_chars: int,
                 system_prompt: bool = True) -> tuple[list[dict], dict]:
    task = ctx.task
    qualname, path = task["caller_qualname"], task["caller_file"]
    kind = "method" if "." in qualname else "function"
    helper_name = task["helper_qualname"].rpartition(".")[2]

    snippets: list[Snippet] = []
    truncated = False
    if condition == "file":
        code, truncated = ctx.file_view(max_file_chars)
        code_title = f"Contents of `{path}`"
        helper_in_code = task["helper_same_module"] and f"def {helper_name}(" in code
    elif condition in ("none", "bm25", "oracle"):
        code, code_title, helper_in_code = ctx.function_view(), f"Excerpt from `{path}`", False
        if condition == "bm25":
            snippets = ctx.retrieve(k)
        elif condition == "oracle":
            snippets = ctx.oracle(k)
    else:
        raise ValueError(f"unknown condition {condition}")

    parts = [
        f"Refactor the {kind} `{qualname}` in `{path}`.",
        INSTRUCTIONS[instruction],
        "Keep its name, signature and behaviour unchanged, and do not modify other functions.",
        f"Reply with the complete new version of `{qualname.rpartition('.')[2]}` in a single "
        "```python code block. If it needs new imports or helper functions, include them in the same block.",
    ]
    if snippets:
        parts.append("Other code in the repository that may be relevant:")
        parts += [f"From `{s.path}`:\n```python\n{s.source}```" for s in snippets]
    parts.append(f"{code_title}:\n```python\n{code}```")
    user = "\n\n".join(parts)

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}] if system_prompt \
        else [{"role": "user", "content": SYSTEM + "\n\n" + user}]
    origins = [s.origin for s in snippets]
    rank = origins.index(task["helper_qualname"]) + 1 if task["helper_qualname"] in origins else None
    meta = {
        "retrieved": origins,
        "helper_rank": rank,
        "helper_in_context": helper_in_code or rank is not None,
        "file_truncated": truncated,
        "prompt_chars": len(user),
    }
    return messages, meta
