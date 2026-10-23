"""Repository snippets and a small BM25 retriever (condition C1 in docs/experiment_design.md)."""
from __future__ import annotations

import ast
import math
import re
import textwrap
from collections import Counter
from dataclasses import dataclass

from .index import RepoIndex

WORD = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")


@dataclass
class Snippet:
    origin: str     # "pkg.module.func" or "pkg.module.Class.method"
    path: str
    source: str


def tokenize(code: str) -> list[str]:
    """Split identifiers in snake_case and camelCase into lower-case words."""
    return [w.lower() for w in WORD.findall(code)]


def repo_snippets(index: RepoIndex, exclude_path: str | None = None) -> list[Snippet]:
    snippets = []
    for name in sorted(index.modules):
        module = index.modules[name]
        if module.path.as_posix() == exclude_path:
            continue
        lines = module.source.splitlines(keepends=True)
        for node in module.tree.body:
            members = [(node, node.name)] if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else []
            if isinstance(node, ast.ClassDef):
                members = [(sub, f"{node.name}.{sub.name}") for sub in node.body
                           if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))]
            for fn, qualname in members:
                first = min([d.lineno for d in fn.decorator_list] + [fn.lineno])
                source = textwrap.dedent("".join(lines[first - 1: fn.end_lineno]))
                snippets.append(Snippet(f"{name}.{qualname}", module.path.as_posix(), source))
    return snippets


def _body_tokens(source: str) -> Counter[str]:
    """Tokens of a function body without its docstring and def line."""
    fn = ast.parse(source).body[0]
    body = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr)
                           and isinstance(fn.body[0].value, ast.Constant)) else fn.body
    return Counter(tokenize(ast.unparse(ast.Module(body=body, type_ignores=[]))))


def equivalent_helpers(snippets: list[Snippet], origin: str, threshold: float = 0.8) -> list[str]:
    """Other repository functions whose body is a near-copy of `origin` (weighted Jaccard >= threshold)."""
    by_origin = {s.origin: s for s in snippets}
    if origin not in by_origin:
        return []
    target = _body_tokens(by_origin[origin].source)
    found = []
    for s in snippets:
        if s.origin == origin:
            continue
        other = _body_tokens(s.source)
        union = sum((target | other).values())
        if union and sum((target & other).values()) / union >= threshold:
            found.append(s.origin)
    return found


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.lengths = [len(d) for d in docs]
        self.avg = sum(self.lengths) / max(len(docs), 1)
        df = Counter(term for d in docs for term in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def top(self, query: list[str], k: int) -> list[int]:
        terms = Counter(query)
        scores = []
        for i, tf in enumerate(self.tf):
            norm = self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg)
            score = sum(self.idf.get(t, 0.0) * qf * tf[t] * (self.k1 + 1) / (tf[t] + norm)
                        for t, qf in terms.items() if t in tf)
            scores.append(score)
        return sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
