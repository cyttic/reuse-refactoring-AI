from collections import Counter

from reuse_bench.build import make_task
from reuse_bench.index import RepoIndex
from reuse_bench.inline import Limits, find_sites, inline
from reuse_bench.prompting import TaskContext, build_prompt, restore_identifier

from test_inline import write_repo

MODULE = '''
import os


def normalize(name, sep="_"):
    cleaned = name.strip().lower()
    parts = cleaned.split()
    return sep.join(parts)


def unrelated(path):
    return os.path.join(path, "x")


def make_key(user, parts):
    key = normalize(user.name)
    return key + str(len(parts))
'''


def context(tmp_path):
    index = write_repo(tmp_path, {"pkg/__init__.py": "", "pkg/m.py": MODULE})
    site = next(s for s in find_sites(index) if s.caller_qualname == "make_key")
    task = make_task(tmp_path, None, inline(index, site, Limits(min_helper_size=1)), Counter())
    return TaskContext(task, tmp_path, RepoIndex.build(tmp_path))


def test_same_module_helper_reaches_the_model_only_through_retrieval(tmp_path):
    ctx = context(tmp_path)
    prompt = lambda condition: build_prompt(ctx, condition, "generic", k=1, max_file_chars=10_000)
    none_msgs, none_meta = prompt("none")
    assert "def normalize(" not in none_msgs[-1]["content"] and not none_meta["helper_in_context"]
    assert "import os" in none_msgs[-1]["content"] and "def make_key(" in none_msgs[-1]["content"]

    oracle_msgs, oracle_meta = prompt("oracle")
    assert "def normalize(" in oracle_msgs[-1]["content"] and oracle_meta["helper_rank"] == 1

    file_msgs, file_meta = prompt("file")
    assert "def normalize(" in file_msgs[-1]["content"] and file_meta["helper_in_context"]


def test_original_target_function_is_never_retrieved(tmp_path):
    ctx = context(tmp_path)
    origins = [s.origin for s in ctx.retrieve(k=10)]
    assert "pkg.m.make_key" not in origins       # the original still calls the helper
    assert "pkg.m.normalize" in origins


def test_position_ablation_moves_only_the_helper(tmp_path):
    ctx = context(tmp_path)
    random_order = ctx.oracle(k=2)
    first, last = ctx.oracle(k=2, position="first"), ctx.oracle(k=2, position="last")
    assert first[0].origin == last[-1].origin == "pkg.m.normalize"
    assert {s.origin for s in first} == {s.origin for s in last} == {s.origin for s in random_order}
    _, meta = build_prompt(ctx, "oracle_last", "generic", k=2, max_file_chars=10_000)
    assert meta["helper_rank"] == 2 and meta["helper_in_context"]


def test_renamed_helper_never_shows_its_real_name(tmp_path):
    ctx = context(tmp_path)
    old, new = ctx.rename
    assert old == "normalize" and new.startswith("fn_")
    for condition in ("none", "oracle", "file"):
        messages, meta = build_prompt(ctx, condition, "reuse", k=2, max_file_chars=10_000, rename_helper=True)
        text = messages[-1]["content"]
        assert "normalize" not in text and meta["renamed"] == [old, new]
        assert (f"def {new}(" in text) == meta["helper_in_context"]


def test_common_or_duplicated_helper_names_are_not_renamed(tmp_path):
    index = write_repo(tmp_path, {"pkg/__init__.py": "", "pkg/m.py": MODULE.replace("normalize", "update")})
    site = next(s for s in find_sites(index) if s.caller_qualname == "make_key")
    task = make_task(tmp_path, None, inline(index, site, Limits(min_helper_size=1)), Counter())
    assert TaskContext(task, tmp_path, RepoIndex.build(tmp_path)).rename is None


def test_output_names_are_restored_and_remembered_names_broken():
    output, from_memory = restore_identifier("x = fn_1(a)\ny = fn_1_b(a)", "normalize", "fn_1")
    assert output == "x = normalize(a)\ny = fn_1_b(a)" and not from_memory
    output, from_memory = restore_identifier("x = self.normalize(a)", "normalize", "fn_1")
    assert output == "x = self.normalize_not_in_prompt(a)" and from_memory
