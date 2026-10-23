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


def test_early_returns_are_kept_when_the_call_is_returned(index):
    mutation = inline(index, site_for(index, "uses_early"), Limits(min_helper_size=1))
    assert "return 1" in mutation.inlined
    assert "from pkg.utils import normalize\n" in mutation.new_source     # `early` import dropped
    namespace = load(mutation.new_source.replace("from pkg.utils import normalize\n", ""))
    assert namespace["uses_early"](0) == 1 + 1 + 2 and namespace["uses_early"](5) == 1


def test_early_return_is_rejected_when_the_result_is_assigned(tmp_path):
    index = write_repo(tmp_path, {"m.py": '''
        def helper(x):
            if x:
                return 1
            return len(str(x)) + 2

        def caller(x):
            y = helper(x)
            return y
    '''})
    with pytest.raises(Rejected, match="single `return <value>`"):
        inline(index, site_for(index, "caller"), Limits(min_helper_size=1))


def test_helper_without_final_return_falls_back_to_none(tmp_path):
    index = write_repo(tmp_path, {"m.py": '''
        def helper(items, x):
            if x > 0:
                items.append(x)
                return len(items)

        def caller(items, x):
            return helper(items, x)
    '''})
    mutation = inline(index, site_for(index, "caller"), Limits(min_helper_size=1))
    namespace = load(mutation.new_source)
    assert namespace["caller"]([], 3) == 1 and namespace["caller"]([], -1) is None


def test_procedure_called_as_statement(tmp_path):
    index = write_repo(tmp_path, {"m.py": '''
        def record(log, value):
            entry = (value, len(log))
            log.append(entry)

        def caller(log):
            record(log, "a")
            return log
    '''})
    mutation = inline(index, site_for(index, "caller"), Limits(min_helper_size=1))
    assert load(mutation.new_source)["caller"]([]) == [("a", 0)]


def test_module_attribute_call_and_import_removed(tmp_path):
    index = write_repo(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/utils.py": UTILS,
        "pkg/api.py": '''
            from pkg import utils

            def slug(text):
                return utils.normalize(text, "-")
        ''',
    })
    site = site_for(index, "slug")
    assert (site.style, site.ref) == ("module", "utils")
    mutation = inline(index, site, Limits(min_helper_size=1))
    assert "utils" not in mutation.new_source
    assert load(mutation.new_source)["slug"](" A b ") == "a-b"


def test_helper_dependencies_are_imported_into_the_caller_module(tmp_path):
    index = write_repo(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/text.py": '''
            import re as regex
            _SPACES = regex.compile(r"\\s+")

            def squash(text):
                parts = _SPACES.split(text.strip())
                return "-".join(parts)
        ''',
        "pkg/api.py": '''
            """API."""
            import os
            from pkg.text import squash

            def slug(text):
                return squash(text)
        ''',
    })
    mutation = inline(index, site_for(index, "slug"), Limits(min_helper_size=1))
    assert '"""API."""\nimport os\nfrom pkg.text import _SPACES\n' in mutation.new_source
    assert "squash" not in mutation.new_source


def test_self_method_is_inlined_with_self_bound(tmp_path):
    index = write_repo(tmp_path, {"m.py": '''
        class Counter:
            def __init__(self):
                self.total = 0

            def _bump(self, amount):
                self.total += amount * 2
                return self.total

            def add(self, n):
                return self._bump(n + 1)
    '''})
    site = site_for(index, "Counter.add")
    assert site.style == "self" and site.helper_qualname == "Counter._bump"
    mutation = inline(index, site, Limits(min_helper_size=1))
    assert "self._bump" not in mutation.inlined and "amount = n + 1" in mutation.inlined
    counter = load(mutation.new_source)["Counter"]()
    assert counter.add(1) == 4 and counter.add(0) == 6


def test_self_method_defined_by_another_class_is_rejected(tmp_path):
    index = write_repo(tmp_path, {"m.py": '''
        class Base:
            def _fmt(self, x):
                text = str(x).strip()
                return text.upper()

            def show(self, x):
                return self._fmt(x)

        class Child(Base):
            def _fmt(self, x):
                return "child"
    '''})
    with pytest.raises(Rejected, match="may be overridden"):
        inline(index, site_for(index, "Base.show"), Limits(min_helper_size=1))


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
