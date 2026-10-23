# Code Reuse / Refactoring with AI — Verified Literature (checked 2026-10-23)

Venue rule from the course: top-ranked IR/NLP/CL conferences, 2025+.
Tier legend: **A** = ACL/EMNLP/NAACL main · **F** = Findings · **I** = Industry track · **SE** = SE journal/conf (not IR/NLP/CL) · **P** = arXiv preprint only.
Summaries are from the official abstracts; read the PDFs before citing specific numbers.

## 1. Original shortlist — all five verified

| # | Paper | Venue (verified) | Tier | Key point | DOI / link |
|---|-------|------------------|------|-----------|------------|
| 1 | **CodeRAG: Finding Relevant and Necessary Knowledge for Retrieval-Augmented Repository-Level Code Completion** — Zhang, Ding, Lian, Song, Li | EMNLP 2025 Main, pp. 23278–23288 | A | Log-prob-based query construction + multi-path retrieval + BestFit reranker aligned to the code LLM; beats SOTA on ReccEval and CCEval. | 10.18653/v1/2025.emnlp-main.1187 |
| 2 | **Beyond Function-Level Search: Repository-Aware Dual-Encoder Code Retrieval with Adversarial Verification** — Liu, Shiyuan, Li, Yang, Qi | Findings of EMNLP 2025, pp. 21034–21049 | F | New RepoAlignBench (change-request-driven retrieval); ReflectCode dual-tower retriever, +12.2% Top-5 acc, +7.1% recall. | 10.18653/v1/2025.findings-emnlp.1147 |
| 3 | **CodeIF: Benchmarking the Instruction-Following Capabilities of LLMs for Code Generation** — Yan, Guo, Shi, Cao, Di, Li | ACL 2025 Industry Track (Vol. 6), pp. 1272–1286 | I | Instruction-following benchmark incl. refactoring tasks across difficulty levels and domains. No headline numbers in abstract. | 10.18653/v1/2025.acl-industry.89 |
| 4 | **Think-Search-Patch: A Retrieval-Augmented Reasoning Framework for Repository-Level Code Repair** — Xiong et al. (14 authors, incl. Deyi Xiong) | EMNLP 2025 Industry Track, pp. 1555–1566 | I | Analyze → build query → retrieve (E5 embeddings) → patch; SFT + DPO on rejection-sampled pairs; better retrieval and repair on SWE-bench Lite, esp. multi-file bugs. | 10.18653/v1/2025.emnlp-industry.109 |
| 5 | **SWE-Refactor: A Repository-Level Benchmark for Real-World LLM-Based Code Refactoring** — Xu, Yang, Chen | arXiv 2602.03712 (Feb 2026), no venue listed | P | 1,099 behavior-preserving refactorings from 18 **Java** projects (922 atomic / 177 compound), validated by compile + tests + refactoring detection; 9 LLMs; Codex agent only 39.4% on compound. | arxiv.org/abs/2602.03712 |

## 2. New finds

### Venue-compliant (ACL family)
| Paper | Venue | Tier | Why it matters for us |
|-------|-------|------|------------------------|
| **On the Impacts of Contexts on Repository-Level Code Generation (RepoExec)** — Le Hai, Nguyen, Bui | Findings of NAACL 2025, pp. 1496–1524 · 10.18653/v1/2025.findings-naacl.82 | F | **Most relevant new find.** Introduces the *Dependency Invocation Rate* — a direct metric for "does the model reuse existing code". Pretrained models often **re-implement existing dependencies** instead of calling them; instruction-tuned models reuse more (+10% DIR). Full dependency context works best. |
| **DependEval: Benchmarking LLMs for Repository Dependency Understanding** | Findings of ACL 2025 (2025.findings-acl.373) | F | Repo-level dependency reasoning; possible baseline task. *Metadata not yet checked on the page.* |
| **SeqCoBench** (functional-equivalence of transformed Python programs) | Findings of NAACL 2025 | F | 20+ semantics-preserving vs. semantics-altering transformations — relevant to behavior-preservation checks. *Exact entry not yet checked.* |

### Strong topical fit, other venues (use for motivation/background)
| Paper | Venue | Tier | Key point |
|-------|-------|------|-----------|
| **More Code, Less Reuse: Investigating Code Quality and Reviewer Sentiment towards AI-generated PRs** — Huang et al. | arXiv 2601.21276 (Jan 2026); author profile suggests MSR 2026 Mining Challenge — *unconfirmed* | SE/P | Agents overlook reuse opportunities → more redundant code (Type-4 semantic clones) than humans; reviewers don't notice. **Core motivation for our project.** |
| **MANTRA: Enhancing Automated Method-Level Refactoring with Contextual RAG and Multi-Agent LLM Collaboration** — Xu, Lin, Yang, Chen, Tsantalis | arXiv 2503.14340 (Mar 2025) | P | RAG + multi-agent + verbal RL; 82.8% of 703 Java refactorings compile+pass tests vs. 8.7% for plain GPT. Closest existing "retrieval for refactoring" system. |
| **RefactorBench: Evaluating Stateful Reasoning in Language Agents Through Code** | ICLR 2025 (arXiv 2503.07832) | ML top venue | 100 multi-file **Python** refactoring tasks; agents solve 22% vs. 87% for humans. Python → reusable for our experiment. |
| **CodeTaste: Can LLMs Generate Human-Level Code Refactorings?** — Thillen, Mündler, Raychev, Vechev | arXiv 2603.04177 (Mar 2026) | P | Agents do well with explicit instructions but fail to *choose* human-like refactorings; "propose-then-implement" helps. |
| **An Empirical Study on the Code Refactoring Capability of LLMs** — Cordeiro, Noei, Zou | ACM TOSEM 2026 · 10.1145/3801158 | SE | 5 LLMs compared on smell reduction and cohesion/coupling metrics. |
| **Can LLMs Identify and Refactor Code Clones? An Empirical Study** | J. Systems & Software vol. 234 (2026) · 10.1016/j.jss.2025.112717 | SE | Clone detection + clone refactoring with GPT-4o, Claude, etc. |
| **An empirical study of LLM-based refactoring consistency** — Zhang, Yuan, Dong | Empirical Software Engineering 2026 · 10.1007/s10664-026-10911-6 | SE | DataRef: 468 Java + 544 Python segments. |
| **Code Copycat Conundrum: Demystifying Repetition in LLM-based Code Generation** | arXiv 2504.12608 (Apr 2025) | P | Repetition in 19 code LLMs; DeRep mitigation. |
| Instruction design for LLM refactoring (Fowler-guided prompts) | arXiv 2510.03914 | P | Fowler-grounded instructions let LLMs perform all refactoring types; DeepSeek-V3 48/48 types vs GPT-4o-mini 14. |

### Checked and discarded
- arXiv 2509.22097 (cited as "ACL 2026 Main") — it is *SecureVibeBench* (secure coding), not refactoring.

## 3. Research gap (emerging)

1. **Reuse is under-measured.** RepoExec (DIR) and "More Code, Less Reuse" show LLMs re-implement instead of reusing, but refactoring benchmarks (SWE-Refactor, MANTRA, CodeTaste) measure behavior preservation and human alignment — **not whether duplicated logic is replaced with calls to existing helpers.**
2. **Language gap.** SWE-Refactor and MANTRA are Java-only; RefactorBench is Python but not reuse-focused.
3. **Retrieval for refactoring is untested in the NLP venues.** CodeRAG / ReflectCode / TSP retrieve for completion or repair; nobody in ACL venues evaluates retrieval specifically for *reuse-oriented refactoring*.

→ Candidate RQ: *Does repository retrieval (CodeRAG/TSP-style) make LLM refactoring reuse existing code more often, while preserving behavior and following instructions (CodeIF-style)?* Metrics: test pass rate, DIR-style reuse rate, duplication reduction, instruction compliance.

## 4. Venue-rule status (for Marina)
- Clearly compliant: CodeRAG (main).
- Need approval: ReflectCode, RepoExec, DependEval, SeqCoBench (Findings); CodeIF, TSP (Industry).
- Background only: SWE-Refactor, MANTRA, CodeTaste, More Code Less Reuse (preprints/SE venues); RefactorBench (ICLR — top ML, not IR/NLP/CL).
- TODO: search ACL 2026 main / EMNLP 2026 / SIGIR 2026 proceedings directly for refactoring or code-reuse papers to strengthen the compliant set.
