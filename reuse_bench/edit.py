"""Extract the model's rewritten function and splice it into the mutated file."""
from __future__ import annotations

import ast
import copy
import re
import textwrap

from .prompting import find_function

CODE_BLOCK = re.compile(r"```[ \t]*(?:python|py|python3)?[ \t]*\n(.*?)```", re.S)
FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


class EditError(Exception):
    """The model output cannot be applied; the message is the reason."""


def extract_code(text: str, name: str) -> str:
    blocks = CODE_BLOCK.findall(text)
    for block in reversed(blocks):
        if re.search(rf"\bdef\s+{re.escape(name)}\s*\(", block):
            return block
    if blocks:
        return blocks[-1]
    unclosed = re.search(r"```[ \t]*(?:python|py|python3)?[ \t]*\n(.*)$", text, re.S)
    if unclosed:
        return unclosed.group(1)    # output hit the token limit before the closing fence
    if re.search(rf"\bdef\s+{re.escape(name)}\s*\(", text):
        return text     # model answered without a code fence
    raise EditError("no code block in output")


def _first_line(node: ast.stmt) -> int:
    return min([d.lineno for d in getattr(node, "decorator_list", [])] + [node.lineno])


def _segment(lines: list[str], node: ast.stmt) -> str:
    return "".join(lines[_first_line(node) - 1: node.end_lineno])


def _bound(node: ast.stmt) -> list[tuple[str, str]]:
    """(name, origin) pairs a top-level statement binds; equal origins mean the same object."""
    if isinstance(node, ast.Import):
        return [(a.asname or a.name.split(".")[0], a.name if a.asname else a.name.split(".")[0])
                for a in node.names]
    if isinstance(node, ast.ImportFrom):
        base = "." * node.level + (node.module or "")
        return [(a.asname or a.name, f"{base}.{a.name}") for a in node.names]
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [(node.name, f"<def {node.name}>")]
    return [(n.id, "<assigned>") for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)]


def _import_line(tree: ast.Module, before: int) -> int:
    """0-based line index after the last top-level import above `before` (or after the docstring)."""
    line = 0
    for i, node in enumerate(tree.body):
        if node.lineno >= before:
            break
        is_doc = i == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        if is_doc or isinstance(node, (ast.Import, ast.ImportFrom)):
            line = node.end_lineno
    return line


def _is_self_import(node: ast.stmt, module_name: str | None) -> bool:
    """`from <this module> import x` inside the module itself refers to the same objects."""
    if not module_name or not isinstance(node, ast.ImportFrom):
        return False
    return (node.level == 0 and node.module == module_name) or \
        (node.level == 1 and node.module == module_name.rpartition(".")[2])


def _is_method_like(node: ast.stmt) -> bool:
    if not isinstance(node, FunctionNode):
        return False
    decorators = {d.id for d in node.decorator_list if isinstance(d, ast.Name)}
    first = node.args.posonlyargs + node.args.args
    return bool(decorators & {"staticmethod", "classmethod", "property"}) or \
        bool(first) and first[0].arg in ("self", "cls")


def apply_edit(source: str, qualname: str, output: str, module_name: str | None = None) -> tuple[str, dict]:
    name = qualname.rpartition(".")[2]
    cls_name = qualname.rpartition(".")[0]
    code = textwrap.dedent(extract_code(output, name))
    try:
        block = ast.parse(code)
    except SyntaxError as exc:
        raise EditError("output does not parse") from exc
    is_fn = lambda n: isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
    defs = [n for n in block.body if is_fn(n)]
    wrapper = None
    if not defs and cls_name:
        # Methods are often answered inside their class (`class Table: ... def method`), as in the prompt.
        wrapper = next((n for n in block.body if isinstance(n, ast.ClassDef) and n.name == cls_name), None)
        defs = [n for n in wrapper.body if is_fn(n)] if wrapper else []
    if not defs:
        raise EditError("output does not define the function")
    new_fn = defs[-1]
    imports = [n for n in block.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    extras = [n for n in block.body if n not in defs and n not in imports and n is not wrapper]

    tree = ast.parse(source)
    target = find_function(tree, qualname)
    # The model may only add *new* names: redefinitions, re-bound imports and other module-level
    # statements would silently change code outside the target, so they are dropped and reported.
    # Verbatim copies of existing code (models often echo their context) change nothing and are skipped.
    existing_dumps = {ast.dump(n) for n in tree.body}
    module_bound: dict[str, set[str]] = {}
    for node in tree.body:
        for bound, origin in _bound(node):
            module_bound.setdefault(bound, set()).add(origin)
    dropped: list[str] = []
    new_methods: list[FunctionNode] = []
    if cls_name:
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
        cls_dumps = {ast.dump(n) for n in cls.body}
        cls_names = {b for n in cls.body for b, _ in _bound(n)}
        # Sibling methods the model wrote, inside the class wrapper or at top level with a `self`/`cls`
        # first parameter: new names are added to the class, existing ones are redefinitions.
        members = [m for m in wrapper.body if m is not new_fn] if wrapper else []
        members += [n for n in extras if _is_method_like(n)]
        extras = [n for n in extras if not _is_method_like(n)]
        for member in members:
            placeholder = isinstance(member, ast.Expr) and isinstance(member.value, ast.Constant)
            if placeholder or ast.dump(member) in cls_dumps:
                continue
            if isinstance(member, FunctionNode) and member.name not in cls_names:
                new_methods.append(member)
            else:
                dropped.append(f"redefines {cls_name}.{getattr(member, 'name', type(member).__name__)}")
    kept_imports = []
    for node in imports:
        if ast.dump(node) in existing_dumps or _is_self_import(node, module_name):
            continue
        keep = []
        for alias, (bound, origin) in zip(node.names, _bound(node)):
            if bound not in module_bound:
                keep.append(alias)
            elif origin not in module_bound[bound]:
                dropped.append(f"import rebinds {bound}")
        if keep:
            node = copy.copy(node)
            node.names = keep
            kept_imports.append(node)
    kept_extras = []
    for node in extras:
        if ast.dump(node) in existing_dumps:
            continue
        names = [b for b, _ in _bound(node)]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign)) \
                and names and not any(n in module_bound for n in names):
            kept_extras.append(node)
        elif any(n in module_bound for n in names):
            dropped.append("redefines " + ", ".join(n for n in names if n in module_bound))
        else:
            dropped.append("module-level statement: " + ast.unparse(node).splitlines()[0][:60])
    imports, extras = kept_imports, kept_extras
    is_method = "." in qualname
    code_lines = code.splitlines(keepends=True)
    lines = source.splitlines(keepends=True)
    indent = " " * target.col_offset

    def text(nodes: list[ast.stmt]) -> str:
        return "\n".join(_segment(code_lines, n).rstrip("\n") + "\n" for n in nodes)

    # (start, end, replacement) on 0-based line ranges, applied bottom-up.
    ops = []
    if is_method:
        method = "\n".join(textwrap.dedent(text([n])) for n in new_methods + [new_fn])
        ops.append((_first_line(target) - 1, target.end_lineno, textwrap.indent(method, indent)))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == qualname.rpartition(".")[0])
        if extras:
            ops.append((_first_line(cls) - 1, _first_line(cls) - 1, text(extras) + "\n\n"))
        anchor = _first_line(cls)
    else:
        ops.append((_first_line(target) - 1, target.end_lineno, text(extras + [new_fn])))
        anchor = _first_line(target)
    existing = {ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))}
    added = [ast.unparse(n) for n in imports if ast.unparse(n) not in existing]
    if added:
        at = _import_line(tree, anchor)
        ops.append((at, at, "".join(a + "\n" for a in added)))
    for start, end, replacement in sorted(ops, key=lambda op: -op[0]):
        lines[start:end] = [replacement]
    new_source = "".join(lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        raise EditError("edited file does not parse") from exc

    info = {
        "new_functions": [n.name for n in extras + new_methods if isinstance(n, FunctionNode)],
        "added_imports": added,
        "signature_kept": ast.dump(target.args) == ast.dump(new_fn.args),
        "dropped": list(dict.fromkeys(dropped)),
        "imports_from": [(n.module, a.name) for n in block.body
                         if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module for a in n.names],
        "compliant": ast.dump(target.args) == ast.dump(new_fn.args) and not dropped,
        "lines_before": target.end_lineno - _first_line(target) + 1,
        "lines_after": new_fn.end_lineno - _first_line(new_fn) + 1,
    }
    return new_source, info
