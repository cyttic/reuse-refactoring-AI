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


def test_method_answered_inside_its_class():
    output = ("```python\nclass Box:\n    ...\n\n    def method(self, x):\n        return x + x\n```")
    new, info = apply_edit(SOURCE, "Box.method", output)
    assert "class Box:\n    def method(self, x):\n        return x + x\n" in new
    assert info["compliant"]


def test_method_wrapper_with_changed_sibling_is_reported():
    output = ("```python\nclass Box:\n    def other(self):\n        return 1\n\n"
              "    def method(self, x):\n        return x + x\n```")
    _, info = apply_edit(SOURCE + "\n    def other(self):\n        return 0\n", "Box.method", output)
    assert info["dropped"] == ["redefines Box.other"]


def test_verbatim_echo_and_self_import_are_not_violations():
    output = ("```python\nimport os\nfrom pkg.m import Box\n\n"
              "class Box:\n    def method(self, x):\n        return x * 2\n\n"
              "def target(x):\n    return x\n```")
    new, info = apply_edit(SOURCE, "target", output, module_name="pkg.m")
    assert info["dropped"] == [] and info["compliant"]
    assert new.count("class Box") == 1 and "from pkg.m import" not in new


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


def test_new_sibling_methods_are_added_to_the_class():
    top_level = ("```python\ndef method(self, x):\n    return self._twice(x)\n\n"
                 "def _twice(self, x):\n    return x * 2\n```")
    wrapped = ("```python\nclass Box:\n    def method(self, x):\n        return self._twice(x)\n\n"
               "    def _twice(self, x):\n        return x * 2\n```")
    for output in (top_level, wrapped):
        new, info = apply_edit(SOURCE, "Box.method", output)
        assert "class Box:\n    def _twice(self, x):\n        return x * 2\n\n    def method(self, x):\n" in new
        assert info["new_functions"] == ["_twice"] and info["compliant"]


def test_top_level_redefinition_of_a_method_is_dropped():
    output = ("```python\ndef method(self, x):\n    return self.method(x)\n\n"
              "def method2(self):\n    return 1\n```")
    source = SOURCE + "\n    def method2(self):\n        return 0\n"
    new, info = apply_edit(source, "Box.method", output)
    assert info["dropped"] == ["redefines Box.method2"] and "return 1" not in new


def test_thinking_is_ignored_even_when_unclosed():
    code = "```python\ndef target(x):\n    return x\n```"
    new, _ = apply_edit(SOURCE, "target", "<think>try ```python\ndef target(x): pass\n```</think>\n" + code)
    assert "    return x\n" in new and "pass" not in new
    with pytest.raises(EditError, match="no code block"):
        apply_edit(SOURCE, "target", "<think>```python\ndef target(x):\n    return x\n```")


def test_fence_with_extra_words_after_the_language():
    new, _ = apply_edit(SOURCE, "target", "```python code block\ndef target(x):\n    return x\n```")
    assert "    return x\n" in new


@pytest.mark.parametrize("first", ["def method(self, x):\n", "# comment\n    def method(self, x):\n"])
def test_method_whose_first_line_lost_its_indentation(first):
    output = "```python\n" + first + "        return x * 3\n\n    def other(self):\n        return 1\n```"
    new, _ = apply_edit(SOURCE, "Box.method", output)
    assert "        return x * 3\n" in new and "    def other(self):\n" in new
