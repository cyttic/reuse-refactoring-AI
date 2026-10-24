## Overall

*compliant*: signature kept and no existing code redefined (violations are dropped before testing); *valid*: tests pass and compliant; *reuses any*: calls the target helper or another repository function the input did not call (check these by hand).

| model | condition | instruction | n | applied | tests pass | compliant | valid | reuses helper | reuses any | valid & reuses helper | defines new helper | hallucinated import |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 129 | 98% (127/129) | 66% (85/129) | 88% (113/129) | 60% (77/129) | 21% (27/129) | 22% (28/129) | 14% (18/129) | 40% (52/129) | 2% (2/129) |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 129 | 97% (125/129) | 61% (79/129) | 88% (113/129) | 56% (72/129) | 43% (55/129) | 45% (58/129) | 32% (41/129) | 25% (32/129) | 6% (8/129) |
| Qwen2.5-Coder-7B-Instruct | file | generic | 129 | 95% (122/129) | 65% (84/129) | 74% (96/129) | 52% (67/129) | 18% (23/129) | 20% (26/129) | 8% (10/129) | 23% (30/129) | 1% (1/129) |
| Qwen2.5-Coder-7B-Instruct | file | reuse | 129 | 91% (118/129) | 67% (87/129) | 71% (92/129) | 52% (67/129) | 22% (28/129) | 25% (32/129) | 9% (12/129) | 18% (23/129) | 3% (4/129) |
| Qwen2.5-Coder-7B-Instruct | none | generic | 129 | 98% (126/129) | 55% (71/129) | 86% (111/129) | 49% (63/129) | 1% (1/129) | 1% (1/129) | 0% (0/129) | 61% (79/129) | 1% (1/129) |
| Qwen2.5-Coder-7B-Instruct | none | reuse | 129 | 96% (124/129) | 53% (68/129) | 82% (106/129) | 43% (56/129) | 3% (4/129) | 5% (6/129) | 0% (0/129) | 75% (97/129) | 6% (8/129) |
| Qwen2.5-Coder-7B-Instruct | oracle | generic | 129 | 99% (128/129) | 66% (85/129) | 86% (111/129) | 59% (76/129) | 38% (49/129) | 38% (49/129) | 22% (29/129) | 41% (53/129) | 2% (2/129) |
| Qwen2.5-Coder-7B-Instruct | oracle | reuse | 129 | 98% (127/129) | 61% (79/129) | 87% (112/129) | 53% (69/129) | 53% (69/129) | 56% (72/129) | 37% (48/129) | 30% (39/129) | 6% (8/129) |


## Reuse funnel

Stages: helper in context → helper called (given in context) → tests pass (given called). Loss columns count tasks lost at each stage; the last column counts reuse without the helper in context (e.g. from training data).

| model | condition | instruction | helper in context | called (of in context) | pass (of called) | lost: not in context | lost: ignored | …of which reused another fn | lost: broken | called without context |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 76% (98/129) | 26% (25/98) | 84% (21/25) | 31 | 73 | 1 | 4 | 2 |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 76% (98/129) | 50% (49/98) | 82% (40/49) | 31 | 49 | 2 | 9 | 6 |
| Qwen2.5-Coder-7B-Instruct | file | generic | 62% (80/129) | 24% (19/80) | 63% (12/19) | 49 | 61 | 1 | 7 | 4 |
| Qwen2.5-Coder-7B-Instruct | file | reuse | 62% (80/129) | 30% (24/80) | 71% (17/24) | 49 | 56 | 3 | 7 | 4 |
| Qwen2.5-Coder-7B-Instruct | none | generic | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 1 |
| Qwen2.5-Coder-7B-Instruct | none | reuse | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 4 |
| Qwen2.5-Coder-7B-Instruct | oracle | generic | 100% (129/129) | 38% (49/129) | 71% (35/49) | 0 | 80 | 0 | 14 | 0 |
| Qwen2.5-Coder-7B-Instruct | oracle | reuse | 100% (129/129) | 53% (69/129) | 75% (52/69) | 0 | 60 | 3 | 17 | 0 |


## Retrieval of the helper (BM25)

| model | condition | instruction | n | recall@k | MRR |
|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 129 | 76% (98/129) | 0.58 |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 129 | 76% (98/129) | 0.58 |
