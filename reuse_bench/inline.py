"""Create a reuse opportunity by inlining a helper H into one of its callers F.

The original F (which calls H) is the reference solution; the mutated F, which
re-implements H's logic, is the task input.
"""
from __future__ import annotations

import ast
import builtins
import copy
from collections.abc import Iterator
from dataclasses import dataclass

from .index import Module, RepoIndex

BUILTIN_NAMES = frozenset(dir(builtins))
FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


class Rejected(Exception):
    """A candidate that cannot become a task; the message is the reason."""


@dataclass
class Limits:
    min_helper_size: int = 8    # stmt + expr nodes in the helper body
    max_helper_lines: int = 30


@dataclass
class Site:
    module: Module              # module containing the caller F
    caller: FunctionNode
    caller_qualname: str
    stmt: ast.stmt              # statement whose value is the call to H
    call: ast.Call
    kind: str                   # "return" | "assign" | "expr"
    helper_module: Module
    helper: ast.FunctionDef


@dataclass
class Mutation:
    site: Site
    new_source: str             # mutated source of the caller module
    inlined: str                # the statements that replaced the call


def _callers(module: Module) -> Iterator[tuple[str, FunctionNode]]:
    for node in module.tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield f"{node.name}.{sub.name}", sub


def _iter_stmts(stmts: list[ast.stmt]) -> Iterator[ast.stmt]:
    """All statements of a function body, without entering nested scopes."""
    for stmt in stmts:
        yield stmt
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for name in ("body", "orelse", "finalbody"):
            yield from _iter_stmts(getattr(stmt, name, None) or [])
        for handler in getattr(stmt, "handlers", None) or []:
            yield from _iter_stmts(handler.body)
        for case in getattr(stmt, "cases", None) or []:
            yield from _iter_stmts(case.body)


def _call_of(stmt: ast.stmt) -> tuple[ast.Call, str] | None:
    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
        return stmt.value, "return"
    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name) and isinstance(stmt.value, ast.Call)):
        return stmt.value, "assign"
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        return stmt.value, "expr"
    return None


def find_sites(index: RepoIndex) -> Iterator[Site]:
    """Every statement-level call from a repository function to a repository helper."""
    for name in sorted(index.modules):
        module = index.modules[name]
        for qualname, caller in _callers(module):
            for stmt in _iter_stmts(caller.body):
                found = _call_of(stmt)
                if not found or not isinstance(found[0].func, ast.Name):
                    continue
                target = index.function(module.bindings.get(found[0].func.id))
                if target is not None:
                    yield Site(module, caller, qualname, stmt, found[0], found[1], *target)


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        return body[1:]
    return body


def local_names(fn: ast.AST) -> set[str]:
    """Names bound inside a function (over-approximated: nested scopes are included)."""
    names = set()
    for node in ast.walk(fn):
        if node is fn:
            continue
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.alias):
            names.add((node.asname or node.name).split(".")[0])
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            names.add(node.rest)
    return names


def free_names(fn: ast.FunctionDef) -> set[str]:
    loaded = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return loaded - local_names(fn)


def check_helper(helper: ast.FunctionDef, limits: Limits) -> list[ast.stmt]:
    """Return the helper body (without docstring) if it can be inlined safely."""
    if helper.decorator_list:
        raise Rejected("helper is decorated")
    args = helper.args
    if args.vararg or args.kwarg or args.kwonlyargs:
        raise Rejected("helper has *args, **kwargs or keyword-only params")
    body = _strip_docstring(helper.body)
    if not body or not isinstance(body[-1], ast.Return) or body[-1].value is None:
        raise Rejected("helper does not end in `return <value>`")
    size = 0
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if isinstance(node, (ast.Yield, ast.YieldFrom, ast.Await)):
            raise Rejected("helper is a generator or coroutine")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            raise Rejected("helper has a nested scope")
        if isinstance(node, (ast.Global, ast.Nonlocal, ast.Import, ast.ImportFrom)):
            raise Rejected("helper has global/nonlocal/import statements")
        if isinstance(node, ast.Return) and node is not body[-1]:
            raise Rejected("helper has an early return")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "\n" in node.value:
            raise Rejected("helper has a multi-line string")
        size += isinstance(node, (ast.stmt, ast.expr))
    if size < limits.min_helper_size:
        raise Rejected("helper is too small")
    if helper.end_lineno - helper.lineno + 1 > limits.max_helper_lines:
        raise Rejected("helper is too long")
    return body


def _bind_args(helper: ast.FunctionDef, call: ast.Call) -> list[tuple[str, ast.expr]]:
    """Map parameters to argument expressions, in the order Python evaluates them."""
    args = helper.args
    posonly = [p.arg for p in args.posonlyargs]
    params = posonly + [p.arg for p in args.args]
    if any(isinstance(a, ast.Starred) for a in call.args) or any(k.arg is None for k in call.keywords):
        raise Rejected("call uses *args or **kwargs")
    if len(call.args) > len(params):
        raise Rejected("call has too many positional arguments")
    bound = list(zip(params, call.args))
    given = {p for p, _ in bound}
    for kw in call.keywords:
        if kw.arg not in params or kw.arg in given or kw.arg in posonly:
            raise Rejected("call has an invalid keyword argument")
        bound.append((kw.arg, kw.value))
        given.add(kw.arg)
    defaults = dict(zip(params[len(params) - len(args.defaults):], args.defaults))
    for p in params:
        if p not in given:
            default = defaults.get(p)
            if not isinstance(default, ast.Constant):
                raise Rejected("missing argument or non-constant default")
            bound.append((p, default))
    return bound


class _Renamer(ast.NodeTransformer):
    def __init__(self, rename: dict[str, str], subst: dict[str, ast.expr]):
        self.rename = rename
        self.subst = subst

    def visit_Name(self, node: ast.Name) -> ast.expr:
        if node.id in self.subst:
            return copy.deepcopy(self.subst[node.id])
        node.id = self.rename.get(node.id, node.id)
        return node

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler:
        if node.name:
            node.name = self.rename.get(node.name, node.name)
        self.generic_visit(node)
        return node


def _same_binding(index: RepoIndex, name: str, helper_module: Module, caller_module: Module) -> bool:
    h, c = helper_module.bindings.get(name), caller_module.bindings.get(name)
    if h is None and c is None:
        return name in BUILTIN_NAMES
    return h is not None and c is not None and index.resolve(h) == index.resolve(c)


def _splice(source: str, stmt: ast.stmt, text: str) -> str:
    lines = source.splitlines(keepends=True)
    indent = lines[stmt.lineno - 1].encode()[: stmt.col_offset].decode()
    tail = lines[stmt.end_lineno - 1].encode()[stmt.end_col_offset:].decode()
    if indent.strip() or tail.strip():
        raise Rejected("call statement shares its line with other code")
    block = "".join(indent + line + "\n" for line in text.splitlines())
    return "".join(lines[: stmt.lineno - 1]) + block + "".join(lines[stmt.end_lineno:])


def _drop_unused_import(source: str, name: str) -> str:
    """Remove `from x import name` if the name is no longer used, so the import does not hint at H."""
    tree = ast.parse(source)
    if any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(tree)):
        return source
    if any(isinstance(n, ast.Constant) and n.value == name for n in ast.walk(tree)):
        return source  # probably listed in __all__
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and any((a.asname or a.name) == name for a in node.names):
            rest = [a for a in node.names if (a.asname or a.name) != name]
            new = ast.unparse(ast.ImportFrom(node.module, rest, node.level)) + "\n" if rest else ""
            return "".join(lines[: node.lineno - 1]) + new + "".join(lines[node.end_lineno:])
    return source


def inline(index: RepoIndex, site: Site, limits: Limits = Limits()) -> Mutation:
    helper, caller, name = site.helper, site.caller, site.call.func.id
    if helper is caller:
        raise Rejected("recursive call")
    body = check_helper(helper, limits)

    caller_locals = local_names(caller)
    if name in caller_locals:
        raise Rejected("helper name is shadowed in the caller")
    if sum(isinstance(n, ast.Name) and n.id == name for n in ast.walk(caller)) != 1:
        raise Rejected("helper is referenced more than once in the caller")
    free = free_names(helper)
    if helper.name in free:
        raise Rejected("helper is recursive")
    for n in free:
        if n in caller_locals:
            raise Rejected("a name used by the helper is shadowed in the caller")
        if not _same_binding(index, n, site.helper_module, site.module):
            raise Rejected("a name used by the helper is not available in the caller module")

    bound = _bind_args(helper, site.call)
    stored = {n.id for n in ast.walk(helper) if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load)}
    # Side-effect-free arguments are substituted directly; the rest get a temporary variable.
    subst = {p: e for p, e in bound if isinstance(e, (ast.Name, ast.Constant)) and p not in stored}

    taken = ({n.id for n in ast.walk(caller) if isinstance(n, ast.Name)}
             | caller_locals | set(site.module.bindings) | free)
    rename = {}
    for local in sorted(local_names(helper) - set(subst)):
        new, k = local, 2
        while new in taken:
            new, k = f"{local}{k}", k + 1
        rename[local] = new
        taken.add(new)

    out: list[ast.stmt] = [
        ast.Assign(targets=[ast.Name(rename[p], ast.Store())], value=copy.deepcopy(e))
        for p, e in bound if p not in subst
    ]
    renamer = _Renamer(rename, subst)
    *head, ret = [renamer.visit(copy.deepcopy(s)) for s in body]
    out += head
    if site.kind == "return":
        out.append(ast.Return(ret.value))
    elif site.kind == "assign":
        out.append(ast.Assign(targets=[copy.deepcopy(site.stmt.targets[0])], value=ret.value))
    elif not isinstance(ret.value, (ast.Name, ast.Constant)):
        out.append(ast.Expr(ret.value))
    if not out:
        raise Rejected("nothing left to inline")

    inlined = ast.unparse(ast.fix_missing_locations(ast.Module(body=out, type_ignores=[])))
    new_source = _splice(site.module.source, site.stmt, inlined)
    if site.helper_module is not site.module:
        new_source = _drop_unused_import(new_source, name)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        raise Rejected("mutated module does not parse") from exc
    return Mutation(site, new_source, inlined)
