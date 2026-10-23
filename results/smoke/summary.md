## Overall

| model | condition | instruction | n | applied | tests pass | reuses helper | reuse & pass | defines new helper |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 1 | 100% (1/1) | 100% (1/1) | 0% (0/1) | 0% (0/1) | 0% (0/1) |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 1 | 100% (1/1) | 0% (0/1) | 0% (0/1) | 0% (0/1) | 0% (0/1) |
| Qwen2.5-Coder-7B-Instruct | file | generic | 1 | 100% (1/1) | 100% (1/1) | 0% (0/1) | 0% (0/1) | 100% (1/1) |
| Qwen2.5-Coder-7B-Instruct | file | reuse | 1 | 100% (1/1) | 100% (1/1) | 0% (0/1) | 0% (0/1) | 100% (1/1) |
| Qwen2.5-Coder-7B-Instruct | none | generic | 1 | 100% (1/1) | 100% (1/1) | 0% (0/1) | 0% (0/1) | 100% (1/1) |
| Qwen2.5-Coder-7B-Instruct | none | reuse | 1 | 100% (1/1) | 100% (1/1) | 0% (0/1) | 0% (0/1) | 100% (1/1) |
| Qwen2.5-Coder-7B-Instruct | oracle | generic | 1 | 100% (1/1) | 100% (1/1) | 0% (0/1) | 0% (0/1) | 0% (0/1) |
| Qwen2.5-Coder-7B-Instruct | oracle | reuse | 1 | 100% (1/1) | 100% (1/1) | 0% (0/1) | 0% (0/1) | 0% (0/1) |


## Reuse funnel

Stages: helper in context → helper called (given in context) → tests pass (given called). Loss columns count tasks lost at each stage; the last column counts reuse without the helper in context (e.g. from training data).

| model | condition | instruction | helper in context | called (of in context) | pass (of called) | lost: not in context | lost: ignored | lost: broken | called without context |
|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 100% (1/1) | 0% (0/1) | – | 0 | 1 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 100% (1/1) | 0% (0/1) | – | 0 | 1 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | file | generic | 100% (1/1) | 0% (0/1) | – | 0 | 1 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | file | reuse | 100% (1/1) | 0% (0/1) | – | 0 | 1 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | none | generic | 0% (0/1) | – | – | 1 | 0 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | none | reuse | 0% (0/1) | – | – | 1 | 0 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | oracle | generic | 100% (1/1) | 0% (0/1) | – | 0 | 1 | 0 | 0 |
| Qwen2.5-Coder-7B-Instruct | oracle | reuse | 100% (1/1) | 0% (0/1) | – | 0 | 1 | 0 | 0 |


## Retrieval of the helper (BM25)

| model | condition | instruction | n | recall@k | MRR |
|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 1 | 100% (1/1) | 0.50 |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 1 | 100% (1/1) | 0.50 |
