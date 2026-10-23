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

| ID | Context given to the model | Inspired by |
|----|----------------------------|-------------|
| C0 | Target file only | Baseline |
| C1 | Lexical retrieval (BM25 / grep) over the repo, top-k snippets | "Better Call Grep" (arXiv 2601.23254) |
| C2 | Dense embedding retrieval, top-k snippets | CodeRAG (EMNLP 2025), ReflectCode (Findings EMNLP 2025) |
| C3 | Agentic search → read → patch loop | Think-Search-Patch (EMNLP 2025 Industry) |
| C4 | Oracle: helper `H` given directly | Upper bound |

Instruction variants (crossed with every condition), following CodeIF (ACL 2025 Industry):
- **I-generic:** "Refactor this function to reduce duplication."
- **I-reuse:** "Refactor this function; prefer existing project functions over new code."

## 5. Models

| Group | Models | Where |
|-------|--------|-------|
| Frontier | 2 API models (e.g. Claude, GPT) | Paid API |
| Open | Qwen2.5-Coder-7B (fp16), Qwen2.5-Coder-32B or DeepSeek-Coder-V2-Lite (4-bit) | A5000 (24 GB) |
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

RQ3 attribution: for each failed task in C1–C3, label **not-retrieved** (`H` ∉ top-k) vs. **retrieved-but-ignored** (`H` ∈ top-k, not called).

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

Known issues / next steps:
1. **Unparse artifacts** leak hints (dead code from substituted defaults, `ast.unparse` formatting)
   → LLM paraphrase step, re-validated with the same tests.
2. **Yield** (~5 tasks/repo) is too low for ~200 tasks → LLM-assisted inlining for helpers with early
   returns, and choose application-style repos with more cross-module helpers.
3. Mined tasks (§3.2) not implemented yet.
