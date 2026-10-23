## Overall

*compliant*: signature kept and no existing code redefined (violations are dropped before testing); *valid*: tests pass and compliant; *reuses any*: calls the target helper or another repository function the input did not call (check these by hand).

| model | condition | instruction | n | applied | tests pass | compliant | valid | reuses helper | reuses any | valid & reuses helper | defines new helper | hallucinated import |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 5 | 100% (5/5) | 80% (4/5) | 20% (1/5) | 20% (1/5) | 40% (2/5) | 40% (2/5) | 0% (0/5) | 20% (1/5) | 20% (1/5) |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 5 | 100% (5/5) | 80% (4/5) | 40% (2/5) | 20% (1/5) | 60% (3/5) | 60% (3/5) | 20% (1/5) | 0% (0/5) | 60% (3/5) |
| Qwen2.5-Coder-7B-Instruct | file | generic | 5 | 100% (5/5) | 80% (4/5) | 60% (3/5) | 40% (2/5) | 40% (2/5) | 40% (2/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) |
| Qwen2.5-Coder-7B-Instruct | file | reuse | 5 | 100% (5/5) | 80% (4/5) | 60% (3/5) | 40% (2/5) | 60% (3/5) | 60% (3/5) | 20% (1/5) | 0% (0/5) | 0% (0/5) |
| Qwen2.5-Coder-7B-Instruct | none | generic | 5 | 100% (5/5) | 40% (2/5) | 20% (1/5) | 20% (1/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 20% (1/5) |
| Qwen2.5-Coder-7B-Instruct | none | reuse | 5 | 100% (5/5) | 80% (4/5) | 20% (1/5) | 20% (1/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 60% (3/5) | 20% (1/5) |
| Qwen2.5-Coder-7B-Instruct | oracle | generic | 5 | 100% (5/5) | 80% (4/5) | 20% (1/5) | 20% (1/5) | 80% (4/5) | 80% (4/5) | 20% (1/5) | 0% (0/5) | 20% (1/5) |
| Qwen2.5-Coder-7B-Instruct | oracle | reuse | 5 | 100% (5/5) | 80% (4/5) | 60% (3/5) | 40% (2/5) | 60% (3/5) | 80% (4/5) | 0% (0/5) | 0% (0/5) | 20% (1/5) |


## Reuse funnel

Stages: helper in context → helper called (given in context) → tests pass (given called). Loss columns count tasks lost at each stage; the last column counts reuse without the helper in context (e.g. from training data).

| model | condition | instruction | helper in context | called (of in context) | pass (of called) | lost: not in context | lost: ignored | …of which reused another fn | lost: broken | called without context |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 80% (4/5) | 50% (2/4) | 100% (2/2) | 1 | 2 | 0 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 80% (4/5) | 75% (3/4) | 100% (3/3) | 1 | 1 | 0 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | file | generic | 100% (5/5) | 40% (2/5) | 50% (1/2) | 0 | 3 | 0 | 1 | 0 |
| Qwen2.5-Coder-7B-Instruct | file | reuse | 100% (5/5) | 60% (3/5) | 67% (2/3) | 0 | 2 | 0 | 1 | 0 |
| Qwen2.5-Coder-7B-Instruct | none | generic | 0% (0/5) | – | – | 5 | 0 | 0 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | none | reuse | 0% (0/5) | – | – | 5 | 0 | 0 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | oracle | generic | 100% (5/5) | 80% (4/5) | 75% (3/4) | 0 | 1 | 0 | 1 | 0 |
| Qwen2.5-Coder-7B-Instruct | oracle | reuse | 100% (5/5) | 60% (3/5) | 67% (2/3) | 0 | 2 | 1 | 1 | 0 |


## Retrieval of the helper (BM25)

| model | condition | instruction | n | recall@k | MRR |
|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 5 | 80% (4/5) | 0.70 |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 5 | 80% (4/5) | 0.70 |
