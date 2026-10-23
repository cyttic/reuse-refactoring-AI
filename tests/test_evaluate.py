from reuse_bench.evaluate import called_origins, hallucinated_imports

from test_inline import write_repo

MODULE = '''
from pkg import util
from pkg.util import helper


class Box:
    def _norm(self, x):
        return x

    def run(self, x):
        a = helper(x)
        b = util.other(a)
        return self._norm(b)
'''


def test_called_origins_resolve_names_modules_and_self_methods(tmp_path):
    index = write_repo(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/util.py": "def helper(x):\n    return x\n\ndef other(x):\n    return x\n",
        "pkg/box.py": MODULE,
    })
    assert called_origins(index, "pkg.box", MODULE, "Box.run") == {
        "pkg.util.helper", "pkg.util.other", "pkg.box.Box._norm"}
    assert index.function("pkg.box.Box._norm") is not None


def test_hallucinated_imports_only_checks_repository_modules(tmp_path):
    index = write_repo(tmp_path, {"pkg/__init__.py": "", "pkg/util.py": "def helper(x):\n    return x\n"})
    found = hallucinated_imports(index, [("pkg.util", "helper"), ("pkg.util", "nope"),
                                         ("pkg.missing", "x"), ("os.path", "join")])
    assert found == ["pkg.util.nope", "pkg.missing.x"]
