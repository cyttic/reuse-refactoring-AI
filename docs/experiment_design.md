# Experiment Design — Retrieval for Reuse-Oriented Refactoring with LLMs

Project 10: Code Reuse / Refactoring with AI · Evgenii Lialin, Roman Vikhman · draft 2026-10-23
Related: [literature_review.md](../literature/literature_review.md)

## 1. Core question

When an LLM refactors code, does it **reuse helpers that already exist in the repository**, or re-implement them?
And does giving it **retrieved repository context** increase reuse **without breaking behavior**?

Motivation: RepoExec (Findings NAACL 2025) shows pretrained models re-implement existing dependencies; "More Code, Less Reuse" (arXiv 2601.21276) shows AI-agent PRs are more redundant than human ones. Existing refactoring benchmarks (SWE-Refactor, MANTRA, CodeTaste, RefactorBench) measure behavior preservation or human alignment, **not reuse** — and most are Java-only.

## 2. Research questions

| RQ | Question |
|----|----------|
| RQ1 | Without repository context, how often do LLMs reuse an existing helper vs. re-implement it when refactoring? |
| RQ2 | Which retrieval strategy (lexical, dense, agentic) most increases reuse without lowering test pass rate? |
| RQ3 | Failure attribution: when reuse fails, was the helper **not retrieved** (retrieval problem) or **retrieved but ignored** (model problem)? |
| RQ4 *(stretch)* | Can an explicit reuse instruction or a small LoRA fine-tune close the gap to the oracle condition? |

## 3. Benchmark construction (Python)

Each task: a target function `F` that duplicates logic already implemented by helper `H` in the same repository. Ideal refactoring = replace the duplicated logic in `F` with a call to `H`.

### 3.1 Injected tasks (~200, controlled ground truth)
1. Select ~10 Python repositories with good test suites (candidates: repos from RefactorBench / RepoExec, plus some created after the models' training cutoffs).
2. Find helpers `H` with at least one call site in a function `F`.
3. Inline `H`'s body into `F` at the call site.
4. Ask an LLM to paraphrase the inlined code (rename variables, restructure) so it becomes a Type-3/4 clone, not verbatim.
5. Keep the task only if the full test suite still passes.
6. Ground truth: the original `F` (calls `H`).

### 3.2 Mined tasks (~50, realistic)
1. Scan git history of the selected repos for commits that **remove duplicated code and add a call to a function that already existed** before the commit.
2. Pre-commit `F` = task input; post-commit `F` = reference.
3. Keep only commits where tests pass before and after.

### 3.3 Contamination control
Report results separately for repos created after the evaluated models' training cutoffs.

## 4. Experimental conditions

All retrieval conditions share the **same base context**: the module's imports plus the target
function. They differ only in the snippets added, so the helper can reach the model *only through
retrieval* (revised 2026-10-23 after Evgenii's gap analysis: in the first version the whole file was
always shown, so same-module helpers — all 5 pilot tasks — leaked into every condition).

| ID | Code name | Context given to the model | Inspired by |
|----|-----------|----------------------------|-------------|
| C0 | `none` | Base context only | Baseline |
| C1 | `bm25` | Base + top-k BM25 snippets from the whole repo (target function excluded) | "Better Call Grep" (arXiv 2601.23254) |
| C2 | — (todo) | Base + top-k dense-retrieval snippets | CodeRAG (EMNLP 2025), CoRet (ACL 2025 short) |
| C3 | — (todo) | Agentic search → read → patch loop; log tool calls | Think-Search-Patch (EMNLP 2025 Industry) |
| C4 | `oracle` | Base + helper among k−1 BM25 distractors (same budget as C1, seeded position) | Upper bound for retrieval |
| Cf | `file` | Whole module (realistic IDE-like view) | Reference |
| C4f / C4l | `oracle_first` / `oracle_last` | Same snippets as C4, helper at rank 1 / rank k (position ablation, opt-in) | Lost-in-the-middle check |

Instruction variants (crossed with every condition), following CodeIF (ACL 2025 Industry):
- **I-generic:** "Refactor this function to reduce duplication."
- **I-reuse:** "Refactor this function; prefer existing project functions over new code."

## 5. Models

| Group | Models | Where |
|-------|--------|-------|
| Frontier | 2 API models (e.g. Claude, GPT) | Paid API |
| Open (small) | Qwen2.5-Coder-7B-Instruct, deepseek-coder-6.7b-instruct (bf16, HF backend) | A5000 (24 GB) |
| Open (2025–26) | Qwen3-Coder-30B-A3B-Instruct (`cyankiwi/...-AWQ-4bit`), Qwen3.8-27B (`RedHatAI/Qwen3.8-27B-INT4`, thinking off) — 4-bit, vLLM 0.32 in `~/env-vllm` | A5000 (24 GB) |
| Stretch (RQ4) | LoRA fine-tune of 7B on mined reuse refactorings | A5000 / Colab Pro |

## 6. Metrics (all automatic)

| Metric | Definition | Tool |
|--------|-----------|------|
| **Test pass rate** | Repository test suite passes after the edit | pytest |
| **Reuse rate** | Refactored `F` calls `H` (DIR-style, cf. RepoExec) | AST analysis |
| **Reinvention rate** | Edit adds a new function that is a clone of `H` | Clone detector |
| **Duplication Δ** | Duplicated lines before vs. after | Clone detector (e.g. jscpd / AST-based) |
| **Instruction compliance** | Edit confined to `F`; public signatures unchanged | Diff + AST checks |
| **Retrieval recall@k** | `H` appears in the top-k retrieved snippets (C1–C3) | Logged retrieval |
| Cost | Tokens / latency per task | Logs |

RQ3 attribution — the **reuse funnel**, the main analysis (`summarize.py`): every task is lost at
exactly one stage — **not in context** (`H` ∉ context) → **ignored** (`H` in context, not called) →
**broken** (called, tests fail) → success. Also reported: Recall@k and MRR of `H` for BM25, and reuse
of `H` *without* it in context (prior knowledge / memorization). All prompts (`prompts.jsonl.gz`)
and applied diffs (`metrics.jsonl`) are stored for manual analysis.

Interpretation guide (from the gap analysis): high recall + low reuse → the model's decision is the
bottleneck; C4 ≫ C1 → retrieval is the bottleneck; C4 also weak → applying the helper is the
bottleneck; reuse but failing tests → helper called incorrectly.

Changes after the smoke run (2026-10-23, 1 task, Qwen2.5-Coder-7B):
- **Compliance is enforced, not just measured.** Model output may only add *new* names. Redefinitions
  of existing functions/variables, imports that re-bind existing names and stray module-level statements
  are dropped before testing and listed in `dropped`; `compliant` = signature kept and nothing dropped;
  **valid** = tests pass and compliant. (The smoke run showed redefinitions such as a stub `_args2cmd`
  that passed the tests only because the original definition came later in the file.)
- **Equivalent helpers.** Near-copies of `H` elsewhere in the repo (body-token weighted Jaccard ≥ 0.8,
  e.g. `strutils.args2sh` ≡ `ecoutils._args2sh` in boltons) count as reusing `H`.
- **`reuses any`** = calls `H`, an equivalent, or any repository function the input did not call; these
  extra cases are reviewed by hand.

Fix after the first full run (qwen7b-v1, 2026-10-24): new helper *methods* the model wrote, either
inside the class wrapper or at top level with a `self`/`cls` parameter, were dropped (wrapper) or put
at module level (top level), so `self._new_helper()` raised `AttributeError` — 232 of 1,032 outputs were
affected. New method names are now added to the class; existing names are still redefinitions. The
affected outputs were re-evaluated.

Manual check: a sample of "not reused" outputs is labelled by hand, since a model may correctly
reuse a *different* equivalent helper (`repo_calls` lists all repository functions called).

## 7. Scale and budget

~250 tasks × 5 conditions × 2 instructions × 4 models ≈ **10,000 runs**.
API cost to be measured on the pilot (1 repo, 1 model) before scaling.

## 8. Timeline

| Phase | Duration | Output |
|-------|----------|--------|
| Benchmark builder + pilot (1 repo, 1 model) | ~3 weeks | Task generator, harness, pilot numbers |
| Full runs | ~3 weeks | All conditions × models |
| Analysis + paper | rest of semester | 4–8 page ACL-style paper |

## 9. Threats to validity
- **Artificial tasks:** injected clones may be easier/harder than real ones → mined subset as a check.
- **Contamination:** popular repos seen in training → post-cutoff repos reported separately.
- **Test-suite weakness:** passing tests ≠ equivalence → only repos with good coverage; inspect a manual sample.
- **Metric validity:** an edit may reuse a *different* valid helper → manual review of a sample of "non-reuse" outcomes.

## 9b. Positioning (after the gap analysis)

`literature/Code_Reuse_Refactoring_Research_Gap_Analysis.md` (Evgenii) shows that "LLM + RAG +
refactoring" (MANTRA, RepoAI), dependency reuse (RepoExec) and code-editing retrieval (CoRet) are
already studied. Our claim is therefore narrower: **locate where reuse is lost — retrieval, the
model's decision, or the edit — under a controlled context budget.** Novelty is not claimed until the
full texts of RepoExec and RepoAI have been read.

## 10. Existing benchmarks — reuse or not?

No established benchmark targets **reuse-oriented refactoring**; that is our gap. Closest ones:

| Benchmark | Venue | Language | What it measures | Use for us |
|-----------|-------|----------|------------------|------------|
| RefactorBench | ICLR 2025 | Python | Multi-file refactoring by agents (100 tasks) | Source repos / secondary eval |
| RepoExec | Findings NAACL 2025 | Python | Repo-level generation, **Dependency Invocation Rate** | Borrow DIR metric; possibly repos |
| SWE-Refactor | arXiv 2026 | Java | Behavior-preserving real refactorings (1,099) | Methodology (validation pipeline) |
| CodeIF | ACL 2025 Industry | multi | Instruction following incl. refactoring | Instruction-compliance design |
| SWE-bench (Lite) | ICLR 2024 | Python | Repo-level issue repair | Used by Think-Search-Patch; not refactoring |
| CCEval, ReccEval | (used by CodeRAG) | Python | Repo-level completion | Retrieval baseline reference |
| RepoAlignBench | Findings EMNLP 2025 | — | Change-request-driven code retrieval | Retriever evaluation reference |

## 11. Decisions
- [x] Python only (2026-10-23).
- [x] RQ4 (fine-tuning) is a stretch goal (2026-10-23).
- [ ] Marina: do Findings / Industry track papers count toward the venue requirement?

## 12. Builder status (`reuse_bench/`)

`python -m reuse_bench.build data/repos/<repo> --out data/tasks/<repo>.jsonl [--pytest-args "... tests"]`

Pipeline: index repo → find statement-level calls `F → H` → deterministically inline `H` into `F`
(argument binding, local renaming, unused-import removal) → baseline tests under coverage →
keep a task only if the call site is **covered** and the suite **still passes** after inlining.
Each task stores a `task_patch` against the pinned `commit`; the original code is the reference.

Pilot on boltons (2026-10-23): 48 call sites → 6 candidates → **5 validated tasks**.
Main rejection reasons: helper has an early return (15), no final `return` (5), too long (5).

Scaling (2026-10-23, after the pilot) — the inliner now also supports:
- `return H(...)` call sites with **early returns** in `H` (each `return` in `H` returns from `F`;
  a missing final `return` becomes `return None`), and **procedures** called as statements;
- **`mod.h(...)`** (function of an imported repo module; the import is dropped if unused) and
  **`self.h(...)`** (method of the caller's class; rejected if any class in the repo defines a method
  of that name, since inlining an overridable method would change subclass behaviour);
- helpers that use names from their own module: the needed imports are added to the caller module
  (whoever duplicated `H` would have needed them too).
Candidates across 12 repos rose from ~63 to ~360 (39 cross-module). Repos, pinned commits and
pytest arguments: `data/repos.json`. `select_tasks.py` keeps every cross-module task and a seeded
sample of same-module tasks, up to 12 per repo. markdown was dropped (tests need pyyaml and a
warnings config the harness cannot run).

Known issues / next steps:
1. **Unparse artifacts** leak hints (dead code from substituted defaults, `ast.unparse` formatting)
   → paraphrase step with an open model, re-validated with the same tests.
2. Mined tasks (§3.2) not implemented yet.

## 13. Results so far (2026-10-25)

Runs: `results/qwen7b-v1` (Qwen2.5-Coder-7B-Instruct), `results/deepseek67b-v1` (deepseek-coder-6.7b-instruct);
129 tasks × 4 conditions × 2 instructions each, HF backend, greedy decoding. DeepSeek's run was interrupted
during evaluation; the last 23 outputs were evaluated locally.

- Both models: the **decision** stage loses most reuse — with the helper guaranteed in context (oracle)
  it is ignored in 60–83 of 129 tasks; retrieval loses 31.
- Without context, reuse is ≈ 0–5% and the model defines its own helper in 48–75% of outputs.
- Whole-module context reuses less than BM25 snippets (18–22% vs 21–47%).
- **Snippet position** may matter: on the 98 tasks where BM25 retrieves the helper, DeepSeek reuses it
  more with BM25 (helper mostly at rank 1) than with the oracle (seeded position): 57 vs 45 (reuse
  instruction). Qwen shows the opposite (49 vs 54). Tested with the `oracle_first` / `oracle_last` ablation
  (same snippets as `oracle`, only the helper's position changes).
- **Position ablation result (2026-10-25)**, helper reused out of 129 (first / random / last):
  Qwen generic 40 / 49 / 41, reuse 63 / 69 / 67 — no position effect (McNemar first vs last p = 1.0, 0.57).
  DeepSeek generic 47 / 46 / 47 — none; **DeepSeek reuse 75 / 58 / 55 — strong primacy effect**
  (25 tasks reused only when first vs 5 only when last, exact McNemar p = 0.0003; valid & reused 41 vs 34).
  This explains DeepSeek's BM25 > oracle result: BM25 usually ranks the helper first (61 of 98 retrieved
  tasks at rank 1), and on retrieved tasks `oracle_first` matches or beats BM25 (61 vs 57).
  Implications: (1) the oracle upper bound must fix the helper's position (use `oracle_first`);
  (2) the primacy effect appears only together with the reuse instruction;
  (3) reordering identical snippets flips the outcome on ~20% of tasks (Qwen: 27/129, DeepSeek reuse:
  30/129), so condition differences must be tested per task (McNemar), not read off headline rates.
- DeepSeek often renames the target function (“output does not define the function”, 61 outputs) —
  counted as not applied.
- **Qwen3-Coder-30B-A3B (4-bit AWQ, vLLM) — `results/qwen3coder30b-v1` (2026-10-25)**, all six conditions.
  Harness fix first: 86 outputs failed to parse because the model writes "```python code" fences or drops the
  indentation of a copied method's first line; both are now handled (54 recovered; no change for the 7B runs).
  Helper reused / valid (tests pass & compliant) out of 129:

  | condition | generic: Qwen7B · DS6.7B · Q3-Coder | reuse: Qwen7B · DS6.7B · Q3-Coder |
  |---|---|---|
  | none | 1/63 · 5/46 · 3/117 | 4/56 · 7/48 · 7/116 |
  | bm25 | 27/77 · 42/58 · 28/117 | 55/72 · 60/58 · 53/112 |
  | oracle | 49/76 · 46/54 · 24/113 | 69/69 · 58/54 · 70/107 |
  | oracle_first | 40/85 · 47/55 · 37/117 | 63/72 · 75/62 · 70/111 |
  | oracle_last | 41/75 · 47/67 · 25/113 | 67/70 · 55/60 · 66/110 |
  | file | 23/67 · 23/60 · 12/120 | 28/67 · 24/55 · 35/114 |

  (1) **The larger, newer model is far more correct (valid 83–93% vs 42–66%) but does not reuse more**:
  paired against Qwen7B, reuse differs significantly only where Qwen3-Coder reuses *less*
  (oracle generic 10 vs 35, p = 0.0002; file generic 4 vs 15, p = 0.02). The reuse decision does not
  improve with scale/recency. Because almost every reuse is also valid, valid & reused is still highest
  for Qwen3-Coder (e.g. oracle reuse 66 vs 48 / 31).
  (2) Without the reuse instruction it rarely reuses (19–29% with the helper guaranteed in context);
  the instruction roughly doubles to triples reuse in every condition with context.
  (3) Position: a primacy effect again, this time with the *generic* instruction (first 37 vs last 25;
  14 vs 2 discordant, p = 0.004; first vs seeded random 15 vs 2, p = 0.002); none with the reuse instruction
  (p = 0.59). So which instruction shows the position effect depends on the model.
  (4) With the reuse instruction BM25 < oracle (53 vs 70, 6 vs 23 discordant, p = 0.002) — unlike DeepSeek;
  the gap is the 31 tasks BM25 does not retrieve.
- **Qwen3.8-27B (INT4, vLLM, thinking off, bf16 KV cache) — `results/qwen38-27b-v1` (2026-10-25).**
  Helper reused / valid out of 129, generic | reuse: none 7/116 | 16/119; bm25 64/119 | 96/119;
  oracle 69/114 | 108/114; oracle_first 78/120 | 110/116; oracle_last 69/119 | 108/113; file 46/124 | 83/120.
  (1) **A step change in reuse**, unlike Qwen3-Coder: paired against both Qwen3-Coder and Qwen7B it reuses
  more in every condition with context (e.g. oracle reuse 41 vs 3 discordant tasks vs Qwen3-Coder,
  p < 1e-8), while staying as correct (valid 88–96%). With the reuse instruction and the helper in context
  it calls it in 84–90% of tasks; the decision stage stops being the bottleneck and retrieval
  (BM25 misses 31 tasks; file context lacks the helper in 49) becomes the main loss.
  So the earlier conclusion holds for coder models up to Qwen3-Coder-30B-A3B, not for the newest
  general model — the paper should frame it as model-dependent, not "scale doesn't help".
  (2) Even this model ignores a visible helper in ~half the tasks without the reuse instruction
  (oracle generic 69/129) — the instruction effect remains large.
  (3) Primacy effect again only with the generic instruction (first 78 vs last 69, 12 vs 3, p = 0.035);
  none with the reuse instruction (near ceiling).
  (4) Caveat — contamination: Qwen3.8 is the most recent model and the repos are public; it reuses the
  helper without seeing it in 16/129 tasks (reuse instruction, `none`; 7 for Qwen3-Coder). Needs a check,
  e.g. tasks from repos/commits after its training cutoff or renamed identifiers.
