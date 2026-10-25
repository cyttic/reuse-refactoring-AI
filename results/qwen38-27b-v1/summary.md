## Overall

*compliant*: signature kept and no existing code redefined (violations are dropped before testing); *valid*: tests pass and compliant; *reuses any*: calls the target helper or another repository function the input did not call (check these by hand).

| model | condition | instruction | n | applied | tests pass | compliant | valid | reuses helper | reuses any | valid & reuses helper | defines new helper | hallucinated import |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B-INT4 | bm25 | generic | 129 | 98% (127/129) | 94% (121/129) | 97% (125/129) | 92% (119/129) | 50% (64/129) | 50% (65/129) | 48% (62/129) | 11% (14/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | bm25 | reuse | 129 | 98% (127/129) | 92% (119/129) | 98% (127/129) | 92% (119/129) | 74% (96/129) | 76% (98/129) | 72% (93/129) | 1% (1/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | file | generic | 129 | 98% (127/129) | 96% (124/129) | 98% (127/129) | 96% (124/129) | 36% (46/129) | 36% (47/129) | 35% (45/129) | 18% (23/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | file | reuse | 129 | 98% (127/129) | 93% (120/129) | 98% (127/129) | 93% (120/129) | 64% (83/129) | 67% (86/129) | 62% (80/129) | 1% (1/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | none | generic | 129 | 98% (126/129) | 93% (120/129) | 95% (122/129) | 90% (116/129) | 5% (7/129) | 5% (7/129) | 2% (3/129) | 16% (20/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | none | reuse | 129 | 98% (126/129) | 93% (120/129) | 97% (125/129) | 92% (119/129) | 12% (16/129) | 12% (16/129) | 11% (14/129) | 5% (6/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | oracle | generic | 129 | 98% (127/129) | 91% (117/129) | 96% (124/129) | 88% (114/129) | 53% (69/129) | 54% (70/129) | 49% (63/129) | 12% (15/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | oracle | reuse | 129 | 98% (127/129) | 89% (115/129) | 98% (126/129) | 88% (114/129) | 84% (108/129) | 84% (109/129) | 81% (105/129) | 0% (0/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | oracle_first | generic | 129 | 98% (127/129) | 94% (121/129) | 98% (126/129) | 93% (120/129) | 60% (78/129) | 60% (78/129) | 59% (76/129) | 11% (14/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | oracle_first | reuse | 129 | 98% (127/129) | 90% (116/129) | 98% (127/129) | 90% (116/129) | 85% (110/129) | 88% (113/129) | 83% (107/129) | 0% (0/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | oracle_last | generic | 129 | 98% (127/129) | 93% (120/129) | 98% (126/129) | 92% (119/129) | 53% (69/129) | 53% (69/129) | 51% (66/129) | 10% (13/129) | 0% (0/129) |
| Qwen3.8-27B-INT4 | oracle_last | reuse | 129 | 98% (127/129) | 88% (113/129) | 98% (127/129) | 88% (113/129) | 84% (108/129) | 84% (109/129) | 81% (105/129) | 0% (0/129) | 0% (0/129) |


## Reuse funnel

Stages: helper in context → helper called (given in context) → tests pass (given called). Loss columns count tasks lost at each stage; the last column counts reuse without the helper in context (e.g. from training data).

| model | condition | instruction | helper in context | called (of in context) | pass (of called) | lost: not in context | lost: ignored | …of which reused another fn | lost: broken | called without context |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B-INT4 | bm25 | generic | 76% (98/129) | 59% (58/98) | 98% (57/58) | 31 | 40 | 1 | 1 | 6 |
| Qwen3.8-27B-INT4 | bm25 | reuse | 76% (98/129) | 87% (85/98) | 96% (82/85) | 31 | 13 | 2 | 3 | 11 |
| Qwen3.8-27B-INT4 | file | generic | 62% (80/129) | 55% (44/80) | 98% (43/44) | 49 | 36 | 0 | 1 | 2 |
| Qwen3.8-27B-INT4 | file | reuse | 62% (80/129) | 90% (72/80) | 96% (69/72) | 49 | 8 | 1 | 3 | 11 |
| Qwen3.8-27B-INT4 | none | generic | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 7 |
| Qwen3.8-27B-INT4 | none | reuse | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 16 |
| Qwen3.8-27B-INT4 | oracle | generic | 100% (129/129) | 53% (69/129) | 93% (64/69) | 0 | 60 | 1 | 5 | 0 |
| Qwen3.8-27B-INT4 | oracle | reuse | 100% (129/129) | 84% (108/129) | 97% (105/108) | 0 | 21 | 1 | 3 | 0 |
| Qwen3.8-27B-INT4 | oracle_first | generic | 100% (129/129) | 60% (78/129) | 97% (76/78) | 0 | 51 | 0 | 2 | 0 |
| Qwen3.8-27B-INT4 | oracle_first | reuse | 100% (129/129) | 85% (110/129) | 97% (107/110) | 0 | 19 | 3 | 3 | 0 |
| Qwen3.8-27B-INT4 | oracle_last | generic | 100% (129/129) | 53% (69/129) | 96% (66/69) | 0 | 60 | 0 | 3 | 0 |
| Qwen3.8-27B-INT4 | oracle_last | reuse | 100% (129/129) | 84% (108/129) | 97% (105/108) | 0 | 21 | 1 | 3 | 0 |


## Retrieval of the helper (BM25)

| model | condition | instruction | n | recall@k | MRR |
|---|---|---|---|---|---|
| Qwen3.8-27B-INT4 | bm25 | generic | 129 | 76% (98/129) | 0.58 |
| Qwen3.8-27B-INT4 | bm25 | reuse | 129 | 76% (98/129) | 0.58 |
