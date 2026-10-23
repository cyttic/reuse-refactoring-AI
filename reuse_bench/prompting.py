"""Build the refactoring prompt for one task under one condition and instruction variant."""
from __future__ import annotations

import ast
import json
from dataclasses import dataclass
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
CONDITIONS = ("file", "bm25", "oracle")   # C0, C1, C4; dense (C2) and agentic (C3) come later


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
        self.function = find_function(ast.parse(self.mutated), task["caller_qualname"])
        self.function_source = "".join(
            self.mutated.splitlines(keepends=True)[self.function.lineno - 1: self.function.end_lineno])
        self.index = index
        self.snippets = repo_snippets(index, exclude_path=task["caller_file"])   # retrieval corpus
        self._bm25: BM25 | None = None

    def retrieve(self, k: int) -> list[Snippet]:
        if self._bm25 is None:
            self._bm25 = BM25([tokenize(s.source) for s in self.snippets])
        return [self.snippets[i] for i in self._bm25.top(tokenize(self.function_source), k)]

    def helper_snippet(self) -> Snippet | None:
        # Search every module: same-module helpers are excluded from the retrieval corpus.
        return next((s for s in repo_snippets(self.index) if s.origin == self.task["helper_qualname"]), None)

    def file_view(self, max_chars: int) -> tuple[str, bool]:
        """The mutated file, or a window around the target function if the file is too long."""
        if len(self.mutated) <= max_chars:
            return self.mutated, False
        lines = self.mutated.splitlines(keepends=True)
        margin = 400
        while margin > 0:
            start = max(0, self.function.lineno - 1 - margin)
            end = min(len(lines), self.function.end_lineno + margin)
            view = "".join(lines[start:end])
            if len(view) <= max_chars:
                break
            margin //= 2
        head = "# ... (earlier lines omitted) ...\n" if start > 0 else ""
        tail = "# ... (later lines omitted) ...\n" if end < len(lines) else ""
        return head + view + tail, True


def build_prompt(ctx: TaskContext, condition: str, instruction: str, k: int, max_file_chars: int,
                 system_prompt: bool = True) -> tuple[list[dict], dict]:
    task = ctx.task
    qualname, path = task["caller_qualname"], task["caller_file"]
    kind = "method" if "." in qualname else "function"

    snippets: list[Snippet] = []
    if condition == "bm25":
        snippets = ctx.retrieve(k)
    elif condition == "oracle":
        snippets = [s for s in [ctx.helper_snippet()] if s]
    elif condition != "file":
        raise ValueError(f"unknown condition {condition}")

    file_text, truncated = ctx.file_view(max_file_chars)
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
    parts.append(f"Contents of `{path}`:\n```python\n{file_text}```")
    user = "\n\n".join(parts)

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}] if system_prompt \
        else [{"role": "user", "content": SYSTEM + "\n\n" + user}]
    origins = [s.origin for s in snippets]
    helper_in_file = task["helper_same_module"] and task["helper_qualname"].rpartition(".")[2] in file_text
    meta = {
        "retrieved": origins,
        "helper_rank": origins.index(task["helper_qualname"]) + 1 if task["helper_qualname"] in origins else None,
        "helper_in_context": helper_in_file or task["helper_qualname"] in origins,
        "file_truncated": truncated,
        "prompt_chars": len(user),
    }
    return messages, meta
