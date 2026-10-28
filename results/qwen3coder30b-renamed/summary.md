## Overall

*compliant*: signature kept and no existing code redefined (violations are dropped before testing); *valid*: tests pass and compliant; *reuses any*: calls the target helper or another repository function the input did not call (check these by hand).

| model | condition | instruction | n | applied | tests pass | compliant | valid | reuses helper | reuses any | valid & reuses helper | defines new helper | hallucinated import |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | generic | 114 | 97% (111/114) | 91% (104/114) | 94% (107/114) | 89% (102/114) | 8% (9/114) | 10% (11/114) | 7% (8/114) | 4% (5/114) | 0% (0/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | reuse | 114 | 97% (111/114) | 89% (101/114) | 94% (107/114) | 88% (100/114) | 32% (36/114) | 33% (38/114) | 30% (34/114) | 0% (0/114) | 0% (0/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | generic | 114 | 97% (111/114) | 91% (104/114) | 96% (110/114) | 90% (103/114) | 7% (8/114) | 9% (10/114) | 7% (8/114) | 4% (5/114) | 0% (0/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | reuse | 114 | 95% (108/114) | 87% (99/114) | 92% (105/114) | 84% (96/114) | 19% (22/114) | 21% (24/114) | 18% (21/114) | 3% (3/114) | 0% (0/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | generic | 114 | 98% (112/114) | 92% (105/114) | 98% (112/114) | 92% (105/114) | 2% (2/114) | 2% (2/114) | 2% (2/114) | 18% (21/114) | 4% (4/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | reuse | 114 | 96% (110/114) | 91% (104/114) | 96% (109/114) | 90% (103/114) | 2% (2/114) | 2% (2/114) | 2% (2/114) | 16% (18/114) | 4% (5/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | generic | 114 | 97% (111/114) | 89% (102/114) | 94% (107/114) | 89% (101/114) | 11% (12/114) | 11% (13/114) | 11% (12/114) | 4% (4/114) | 0% (0/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | reuse | 114 | 97% (111/114) | 88% (100/114) | 93% (106/114) | 87% (99/114) | 40% (46/114) | 43% (49/114) | 38% (43/114) | 1% (1/114) | 0% (0/114) |


## Reuse funnel

Stages: helper in context → helper called (given in context) → tests pass (given called). Loss columns count tasks lost at each stage; the last column counts reuse without the helper in context (e.g. from training data).

| model | condition | instruction | helper in context | called (of in context) | pass (of called) | lost: not in context | lost: ignored | …of which reused another fn | lost: broken | called without context |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | generic | 73% (83/114) | 7% (6/83) | 83% (5/6) | 31 | 77 | 1 | 1 | 3 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | reuse | 73% (83/114) | 37% (31/83) | 94% (29/31) | 31 | 52 | 1 | 2 | 5 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | generic | 59% (67/114) | 10% (7/67) | 100% (7/7) | 47 | 60 | 0 | 0 | 1 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | reuse | 59% (67/114) | 31% (21/67) | 95% (20/21) | 47 | 46 | 0 | 1 | 1 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | generic | 0% (0/114) | – | – | 114 | 0 | 0 | 0 | 2 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | reuse | 0% (0/114) | – | – | 114 | 0 | 0 | 0 | 2 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | generic | 100% (114/114) | 11% (12/114) | 100% (12/12) | 0 | 102 | 1 | 0 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | reuse | 100% (114/114) | 40% (46/114) | 93% (43/46) | 0 | 68 | 3 | 3 | 0 |


## Retrieval of the helper (BM25)

| model | condition | instruction | n | recall@k | MRR |
|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | generic | 114 | 73% (83/114) | 0.57 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | reuse | 114 | 73% (83/114) | 0.57 |


## Contamination check: helper renamed in the prompt

*uses original name*: the output names the helper as in the real repository although the prompt only showed the neutral name, i.e. from memory (counted as not reusing).

| model | condition | instruction | n | reuses helper (shown name) | uses original name |
|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | generic | 114 | 8% (9/114) | 1% (1/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | reuse | 114 | 32% (36/114) | 0% (0/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | generic | 114 | 7% (8/114) | 2% (2/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | reuse | 114 | 19% (22/114) | 0% (0/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | generic | 114 | 2% (2/114) | 0% (0/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | reuse | 114 | 2% (2/114) | 2% (2/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | generic | 114 | 11% (12/114) | 0% (0/114) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | reuse | 114 | 40% (46/114) | 0% (0/114) |
