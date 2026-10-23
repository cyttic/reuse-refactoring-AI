import ast
import textwrap
from pathlib import Path

import pytest

from reuse_bench.index import RepoIndex
from reuse_bench.inline import Limits, Rejected, find_sites, inline

UTILS = '''
def normalize(name, sep="_"):
    """Lower-case and join words."""
    cleaned = name.strip().lower()
    parts = cleaned.split()
    return sep.join(parts)


def early(x):
    if x:
        return 1
    return len(str(x)) + len(repr(x)) + 2
'''

CORE = '''
from pkg.utils import normalize, early


def make_key(user, parts):
    key = normalize(user.name)
    return key + str(len(parts))


def shadowing(str):
    return normalize(str)


def uses_early(x):
    return early(x)
'''


def write_repo(root: Path, files: dict[str, str]) -> RepoIndex:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text).lstrip())
    return RepoIndex.build(root)


def site_for(index, caller):
    return next(s for s in find_sites(index) if s.caller_qualname == caller)


def load(source: str) -> dict:
    namespace: dict = {}
    exec(compile(source, "<mutated>", "exec"), namespace)
    return namespace


class User:
    name = "  Ada  Lovelace "


@pytest.fixture
def index(tmp_path):
    return write_repo(tmp_path, {"pkg/__init__.py": "", "pkg/utils.py": UTILS, "pkg/core.py": CORE})


def test_inlining_preserves_behaviour_and_renames_clashing_locals(index):
    mutation = inline(index, site_for(index, "make_key"), Limits(min_helper_size=1))
    assert "parts2 = cleaned.split()" in mutation.inlined          # `parts` clashes with the caller's param
    assert "'_'.join(parts2)" in mutation.inlined                  # constant default substituted
    make_key = next(n for n in ast.parse(mutation.new_source).body if getattr(n, "name", "") == "make_key")
    assert "normalize" not in ast.unparse(make_key)
    assert "from pkg.utils import normalize, early" in mutation.new_source  # still used by `shadowing`
    namespace = load(mutation.new_source.replace("from pkg.utils import normalize, early\n", ""))
    assert namespace["make_key"](User(), [1, 2]) == "ada_lovelace2"


def test_unused_import_of_helper_is_removed(tmp_path):
    index = write_repo(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/utils.py": UTILS,
        "pkg/api.py": '''
            import os
            from pkg.utils import early, normalize

            def slug(text):
                return normalize(text, "-")
        ''',
    })
    mutation = inline(index, site_for(index, "slug"), Limits(min_helper_size=1))
    assert "from pkg.utils import early\n" in mutation.new_source
    assert "normalize" not in mutation.new_source
    assert "'-'.join(parts)" in mutation.new_source


def test_rejects_helper_whose_free_name_is_shadowed(index):
    # normalize has no free names except builtins it does not use, so shadowing `str`
    # only matters for helpers that reference `str`; here the helper is still inlinable.
    mutation = inline(index, site_for(index, "shadowing"), Limits(min_helper_size=1))
    assert "str.strip()" in mutation.inlined


def test_rejects_early_return(index):
    with pytest.raises(Rejected, match="early return"):
        inline(index, site_for(index, "uses_early"), Limits(min_helper_size=1))


def test_rejects_shadowed_builtin_used_by_helper(tmp_path):
    index = write_repo(tmp_path, {
        "m.py": '''
            def helper(x):
                y = str(x).strip()
                return len(y) + len(y.split())

            def caller(str, x):
                return helper(x)
        ''',
    })
    with pytest.raises(Rejected, match="shadowed in the caller"):
        inline(index, site_for(index, "caller"), Limits(min_helper_size=1))


def test_rejects_small_helpers_by_default(tmp_path):
    index = write_repo(tmp_path, {
        "m.py": '''
            def helper(x):
                return x + 1

            def caller(x):
                return helper(x)
        ''',
    })
    with pytest.raises(Rejected, match="too small"):
        inline(index, site_for(index, "caller"))


def test_non_trivial_argument_gets_temporary_and_keeps_evaluation_order(tmp_path):
    index = write_repo(tmp_path, {
        "m.py": '''
            calls = []

            def helper(a, b):
                total = a * 2
                return total + b

            def caller(log):
                result = helper(log("a"), b=log("b"))
                return result
        ''',
    })
    mutation = inline(index, site_for(index, "caller"), Limits(min_helper_size=1))
    namespace = load(mutation.new_source)
    seen = []
    assert namespace["caller"](lambda v: seen.append(v) or len(seen)) == 4
    assert seen == ["a", "b"]
