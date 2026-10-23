"""Create a reuse opportunity by inlining a helper H into one of its callers F.

The original F (which calls H) is the reference solution; the mutated F, which
re-implements H's logic, is the task input.

Supported call styles: `h(...)` (function imported or defined in the module), `mod.h(...)`
(function of an imported repository module) and `self.h(...)` (method of the caller's class).
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
    helper_qualname: str        # "h" or "Class.h", relative to helper_module
    style: str                  # "name" | "module" | "self"
    ref: str                    # name in F that the call goes through: h, the module alias, or self


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


def _self_name(caller: FunctionNode) -> str | None:
    """Name of the instance parameter of a plain method."""
    decorators = {d.id for d in caller.decorator_list if isinstance(d, ast.Name)}
    if decorators & {"staticmethod", "classmethod"} or not caller.args.args:
        return None
    return caller.args.args[0].arg


def find_sites(index: RepoIndex) -> Iterator[Site]:
    """Every statement-level call from a repository function to a repository helper."""
    for name in sorted(index.modules):
        module = index.modules[name]
        for qualname, caller in _callers(module):
            cls = qualname.split(".")[0] if "." in qualname else None
            self_name = _self_name(caller) if cls else None
            for stmt in _iter_stmts(caller.body):
                found = _call_of(stmt)
                if not found:
                    continue
                call, kind = found
                func = call.func
                if isinstance(func, ast.Name):
                    target = index.function(module.bindings.get(func.id))
                    if target and target[1] is target[0].functions.get(target[1].name):
                        yield Site(module, caller, qualname, stmt, call, kind, *target,
                                   target[1].name, "name", func.id)
                elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    ref = func.value.id
                    if ref == self_name and func.attr in module.methods.get(cls, {}):
                        yield Site(module, caller, qualname, stmt, call, kind, module,
                                   module.methods[cls][func.attr], f"{cls}.{func.attr}", "self", ref)
                    elif ref in module.bindings:
                        origin = index.resolve(module.bindings[ref])
                        helper_module = index.modules.get(origin)
                        if helper_module and func.attr in helper_module.functions:
                            yield Site(module, caller, qualname, stmt, call, kind, helper_module,
                                       helper_module.functions[func.attr], func.attr, "module", ref)


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
    """Return the helper body (without docstring) if it can be inlined safely.

    How `return` statements are handled depends on the call site and is checked in `inline`.
    """
    if helper.decorator_list:
        raise Rejected("helper is decorated")
    args = helper.args
    if args.vararg or args.kwarg or args.kwonlyargs:
        raise Rejected("helper has *args, **kwargs or keyword-only params")
    body = _strip_docstring(helper.body)
    if not body:
        raise Rejected("helper has no body")
    size = 0
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if isinstance(node, (ast.Yield, ast.YieldFrom, ast.Await)):
            raise Rejected("helper is a generator or coroutine")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            raise Rejected("helper has a nested scope")
        if isinstance(node, (ast.Global, ast.Nonlocal, ast.Import, ast.ImportFrom)):
            raise Rejected("helper has global/nonlocal/import statements")
        size += isinstance(node, (ast.stmt, ast.expr))
    if size < limits.min_helper_size:
        raise Rejected("helper is too small")
    if helper.end_lineno - helper.lineno + 1 > limits.max_helper_lines:
        raise Rejected("helper is too long")
    return body


def _check_returns(body: list[ast.stmt], kind: str) -> None:
    """Which `return` layouts can be inlined at which kind of call site."""
    returns = [n for n in ast.walk(ast.Module(body=body, type_ignores=[])) if isinstance(n, ast.Return)]
    single_final = len(returns) == 1 and returns[0] is body[-1]
    if kind == "return":
        return      # every `return` in H also returns from F: always equivalent
    if kind == "assign" and not (single_final and body[-1].value is not None):
        raise Rejected("helper is assigned but does not end in a single `return <value>`")
    if kind == "expr" and returns and not single_final:
        raise Rejected("helper has an early return")


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
    """Remove the import binding `name` if it is no longer used, so the import does not hint at H."""
    tree = ast.parse(source)
    if any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(tree)):
        return source
    if any(isinstance(n, ast.Constant) and n.value == name for n in ast.walk(tree)):
        return source  # probably listed in __all__
    lines = source.splitlines(keepends=True)
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        bound = lambda a: a.asname or (a.name if isinstance(node, ast.ImportFrom) else a.name.split(".")[0])
        if any(bound(a) == name for a in node.names):
            rest = [a for a in node.names if bound(a) != name]
            if not rest:
                new = ""
            elif isinstance(node, ast.ImportFrom):
                new = ast.unparse(ast.ImportFrom(node.module, rest, node.level)) + "\n"
            else:
                new = ast.unparse(ast.Import(rest)) + "\n"
            return "".join(lines[: node.lineno - 1]) + new + "".join(lines[node.end_lineno:])
    return source


def _import_for(name: str, origin: str) -> str:
    """An import statement that binds `name` to `origin` (a module, or an attribute of one)."""
    base, _, attr = origin.rpartition(".")
    if not base:
        return f"import {origin}" if origin == name else f"import {origin} as {name}"
    return f"from {base} import {attr}" if attr == name else f"from {base} import {attr} as {name}"


def _add_imports(source: str, imports: list[str]) -> str:
    """Insert imports after the last top-level import (or the module docstring)."""
    tree = ast.parse(source)
    line = 0
    for i, node in enumerate(tree.body):
        is_doc = i == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        if is_doc or isinstance(node, (ast.Import, ast.ImportFrom)):
            line = node.end_lineno
        elif line:
            break
    lines = source.splitlines(keepends=True)
    return "".join(lines[:line]) + "".join(i + "\n" for i in imports) + "".join(lines[line:])


def _references(caller: FunctionNode, site: Site) -> int:
    """How often F refers to H through the name the call uses."""
    if site.style == "name":
        return sum(isinstance(n, ast.Name) and n.id == site.ref for n in ast.walk(caller))
    attr = site.helper.name
    return sum(isinstance(n, ast.Attribute) and n.attr == attr and isinstance(n.value, ast.Name)
               and n.value.id == site.ref for n in ast.walk(caller))


def inline(index: RepoIndex, site: Site, limits: Limits = Limits()) -> Mutation:
    helper, caller = site.helper, site.caller
    if helper is caller:
        raise Rejected("recursive call")
    body = check_helper(helper, limits)
    _check_returns(body, site.kind)

    caller_locals = local_names(caller)
    if site.style != "self" and site.ref in caller_locals:
        raise Rejected("helper name is shadowed in the caller")
    if _references(caller, site) != 1:
        raise Rejected("helper is referenced more than once in the caller")
    if site.style == "self":
        if index.method_definers(helper.name) > 1:
            raise Rejected("helper method is defined by several classes (may be overridden)")
        if any(isinstance(n, ast.Attribute) and n.attr == helper.name for n in ast.walk(helper)):
            raise Rejected("helper is recursive")
    free = free_names(helper)
    if helper.name in free:
        raise Rejected("helper is recursive")
    # Names H uses from its own module are imported into F's module, as whoever duplicated H would have.
    needed_imports = []
    for n in sorted(free):
        if n in caller_locals:
            raise Rejected("a name used by the helper is shadowed in the caller")
        if _same_binding(index, n, site.helper_module, site.module):
            continue
        if n in site.module.bindings or n not in site.helper_module.bindings:
            raise Rejected("a name used by the helper is not available in the caller module")
        needed_imports.append(_import_for(n, site.helper_module.bindings[n]))

    call = site.call
    if site.style == "self":   # self.h(a) is h(self, a)
        call = ast.Call(func=call.func, args=[ast.Name(site.ref, ast.Load()), *call.args], keywords=call.keywords)
    bound = _bind_args(helper, call)
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
    renamed = [renamer.visit(copy.deepcopy(s)) for s in body]
    if site.kind == "return":
        out += renamed
        if not isinstance(renamed[-1], ast.Return):
            out.append(ast.Return(None))     # H fell off its end, so `return H(...)` returned None
    elif isinstance(renamed[-1], ast.Return):
        *head, ret = renamed
        out += head
        if site.kind == "assign":
            out.append(ast.Assign(targets=[copy.deepcopy(site.stmt.targets[0])], value=ret.value))
        elif ret.value is not None and not isinstance(ret.value, (ast.Name, ast.Constant)):
            out.append(ast.Expr(ret.value))
    else:
        out += renamed                      # a procedure called as a statement
    if not out:
        raise Rejected("nothing left to inline")

    inlined = ast.unparse(ast.fix_missing_locations(ast.Module(body=out, type_ignores=[])))
    if '"""' in inlined or "'''" in inlined:
        raise Rejected("inlined code has a docstring-like string")   # re-indenting would change it
    new_source = _splice(site.module.source, site.stmt, inlined)
    if site.style != "self" and site.helper_module is not site.module:
        new_source = _drop_unused_import(new_source, site.ref)
    if needed_imports:
        new_source = _add_imports(new_source, needed_imports)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        raise Rejected("mutated module does not parse") from exc
    return Mutation(site, new_source, inlined)
