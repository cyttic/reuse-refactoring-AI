## Overall

*compliant*: signature kept and no existing code redefined (violations are dropped before testing); *valid*: tests pass and compliant; *reuses any*: calls the target helper or another repository function the input did not call (check these by hand).

| model | condition | instruction | n | applied | tests pass | compliant | valid | reuses helper | reuses any | valid & reuses helper | defines new helper | hallucinated import |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B-INT4 | bm25 | generic | 114 | 98% (112/114) | 90% (103/114) | 96% (110/114) | 89% (101/114) | 19% (22/114) | 19% (22/114) | 18% (21/114) | 22% (25/114) | 0% (0/114) |
| Qwen3.8-27B-INT4 | bm25 | reuse | 114 | 98% (112/114) | 88% (100/114) | 98% (112/114) | 88% (100/114) | 54% (62/114) | 56% (64/114) | 53% (60/114) | 1% (1/114) | 2% (2/114) |
| Qwen3.8-27B-INT4 | file | generic | 114 | 98% (112/114) | 96% (109/114) | 98% (112/114) | 96% (109/114) | 18% (21/114) | 19% (22/114) | 18% (21/114) | 27% (31/114) | 0% (0/114) |
| Qwen3.8-27B-INT4 | file | reuse | 114 | 98% (112/114) | 93% (106/114) | 98% (112/114) | 93% (106/114) | 52% (59/114) | 54% (61/114) | 50% (57/114) | 2% (2/114) | 0% (0/114) |
| Qwen3.8-27B-INT4 | none | generic | 114 | 97% (111/114) | 94% (107/114) | 97% (111/114) | 94% (107/114) | 2% (2/114) | 2% (2/114) | 2% (2/114) | 20% (23/114) | 1% (1/114) |
| Qwen3.8-27B-INT4 | none | reuse | 114 | 97% (111/114) | 93% (106/114) | 97% (111/114) | 93% (106/114) | 2% (2/114) | 2% (2/114) | 2% (2/114) | 6% (7/114) | 0% (0/114) |
| Qwen3.8-27B-INT4 | oracle | generic | 114 | 98% (112/114) | 92% (105/114) | 96% (110/114) | 90% (103/114) | 29% (33/114) | 30% (34/114) | 27% (31/114) | 19% (22/114) | 0% (0/114) |
| Qwen3.8-27B-INT4 | oracle | reuse | 114 | 98% (112/114) | 89% (101/114) | 97% (111/114) | 88% (100/114) | 72% (82/114) | 74% (84/114) | 71% (81/114) | 0% (0/114) | 1% (1/114) |


## Reuse funnel

Stages: helper in context → helper called (given in context) → tests pass (given called). Loss columns count tasks lost at each stage; the last column counts reuse without the helper in context (e.g. from training data).

| model | condition | instruction | helper in context | called (of in context) | pass (of called) | lost: not in context | lost: ignored | …of which reused another fn | lost: broken | called without context |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B-INT4 | bm25 | generic | 73% (83/114) | 24% (20/83) | 95% (19/20) | 31 | 63 | 0 | 1 | 2 |
| Qwen3.8-27B-INT4 | bm25 | reuse | 73% (83/114) | 70% (58/83) | 97% (56/58) | 31 | 25 | 2 | 2 | 4 |
| Qwen3.8-27B-INT4 | file | generic | 59% (67/114) | 30% (20/67) | 100% (20/20) | 47 | 47 | 0 | 0 | 1 |
| Qwen3.8-27B-INT4 | file | reuse | 59% (67/114) | 79% (53/67) | 96% (51/53) | 47 | 14 | 0 | 2 | 6 |
| Qwen3.8-27B-INT4 | none | generic | 0% (0/114) | – | – | 114 | 0 | 0 | 0 | 2 |
| Qwen3.8-27B-INT4 | none | reuse | 0% (0/114) | – | – | 114 | 0 | 0 | 0 | 2 |
| Qwen3.8-27B-INT4 | oracle | generic | 100% (114/114) | 29% (33/114) | 94% (31/33) | 0 | 81 | 1 | 2 | 0 |
| Qwen3.8-27B-INT4 | oracle | reuse | 100% (114/114) | 72% (82/114) | 99% (81/82) | 0 | 32 | 2 | 1 | 0 |


## Retrieval of the helper (BM25)

| model | condition | instruction | n | recall@k | MRR |
|---|---|---|---|---|---|
| Qwen3.8-27B-INT4 | bm25 | generic | 114 | 73% (83/114) | 0.57 |
| Qwen3.8-27B-INT4 | bm25 | reuse | 114 | 73% (83/114) | 0.57 |


## Contamination check: helper renamed in the prompt

*uses original name*: the output names the helper as in the real repository although the prompt only showed the neutral name, i.e. from memory (counted as not reusing).

| model | condition | instruction | n | reuses helper (shown name) | uses original name |
|---|---|---|---|---|---|
| Qwen3.8-27B-INT4 | bm25 | generic | 114 | 19% (22/114) | 2% (2/114) |
| Qwen3.8-27B-INT4 | bm25 | reuse | 114 | 54% (62/114) | 2% (2/114) |
| Qwen3.8-27B-INT4 | file | generic | 114 | 18% (21/114) | 4% (5/114) |
| Qwen3.8-27B-INT4 | file | reuse | 114 | 52% (59/114) | 1% (1/114) |
| Qwen3.8-27B-INT4 | none | generic | 114 | 2% (2/114) | 3% (3/114) |
| Qwen3.8-27B-INT4 | none | reuse | 114 | 2% (2/114) | 3% (3/114) |
| Qwen3.8-27B-INT4 | oracle | generic | 114 | 29% (33/114) | 2% (2/114) |
| Qwen3.8-27B-INT4 | oracle | reuse | 114 | 72% (82/114) | 0% (0/114) |
