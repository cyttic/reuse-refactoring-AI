import difflib
import textwrap

import pytest

from reuse_bench.edit import EditError, apply_edit
from reuse_bench.patching import apply_patch

SOURCE = textwrap.dedent('''
    """Module doc."""
    import os


    def target(x):
        y = x.strip()
        return y.lower()


    class Box:
        def method(self, x):
            return x * 2
''').lstrip()


def test_function_replaced_and_import_hoisted():
    output = "Sure:\n```python\nfrom pkg.text import clean\n\ndef target(x):\n    return clean(x)\n```\n"
    new, info = apply_edit(SOURCE, "target", output)
    assert "import os\nfrom pkg.text import clean\n" in new
    assert "    return clean(x)\n" in new and "y.lower()" not in new
    assert info["added_imports"] == ["from pkg.text import clean"]
    assert info["signature_kept"] and info["lines_after"] == 2


def test_method_is_reindented_and_extra_helper_goes_to_module_level():
    output = "```python\ndef _double(v):\n    return v + v\n\ndef method(self, x):\n    return _double(x)\n```"
    new, info = apply_edit(SOURCE, "Box.method", output)
    assert "def _double(v):\n    return v + v\n\n\nclass Box:" in new
    assert "    def method(self, x):\n        return _double(x)\n" in new
    assert info["new_functions"] == ["_double"]


def test_redefinitions_and_rebinding_imports_are_dropped_and_reported():
    output = ("```python\nimport os\nfrom pkg import Box\nfrom pkg.text import clean\nLIMIT = 3\nVERSION = 2\n"
              "if True:\n    pass\n\n"
              "def target(x):\n    return clean(x)[:LIMIT]\n\n"
              "class Box:\n    pass\n```")
    new, info = apply_edit(SOURCE.replace("import os\n", "import os\nVERSION = 1\n"), "target", output)
    assert info["dropped"] == ["import rebinds Box", "redefines VERSION", "module-level statement: if True:",
                               "redefines Box"]
    assert not info["compliant"]
    assert "from pkg.text import clean\n" in new and "from pkg import Box" not in new  # identical `import os` skipped
    assert "LIMIT = 3\n" in new and "VERSION = 2" not in new
    assert new.count("class Box") == 1


def test_unclosed_code_block_is_accepted():
    new, _ = apply_edit(SOURCE, "target", "```python\ndef target(x):\n    return x.strip()\n")
    assert "    return x.strip()\n" in new and "y.lower()" not in new


def test_signature_change_is_reported():
    _, info = apply_edit(SOURCE, "target", "```python\ndef target(x, strict=False):\n    return x\n```")
    assert not info["signature_kept"]


@pytest.mark.parametrize("output, reason", [
    ("no code here", "no code block"),
    ("```python\ndef target(x):\n    return (\n```", "does not parse"),
    ("```python\ndef other(x):\n    return x\n```", "does not define"),
])
def test_unusable_outputs(output, reason):
    with pytest.raises(EditError, match=reason):
        apply_edit(SOURCE, "target", output)


def test_patch_round_trip():
    new = SOURCE.replace("y = x.strip()", "y = x.strip()\n    y = y.replace('-', '_')")
    patch = "".join(difflib.unified_diff(SOURCE.splitlines(keepends=True), new.splitlines(keepends=True),
                                         fromfile="a/m.py", tofile="b/m.py"))
    assert apply_patch(SOURCE, patch) == new
    with pytest.raises(ValueError, match="does not apply"):
        apply_patch(SOURCE.replace("return y.lower()", "return y.upper()"), patch)
