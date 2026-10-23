## Overall

*compliant*: signature kept and no existing code redefined (violations are dropped before testing); *valid*: tests pass and compliant; *reuses any*: calls the target helper or another repository function the input did not call (check these by hand).

| model | condition | instruction | n | applied | tests pass | compliant | valid | reuses helper | reuses any | valid & reuses helper | defines new helper | hallucinated import |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 129 | 98% (127/129) | 49% (63/129) | 81% (104/129) | 44% (57/129) | 21% (27/129) | 22% (28/129) | 13% (17/129) | 30% (39/129) | 2% (2/129) |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 129 | 97% (125/129) | 53% (68/129) | 81% (105/129) | 48% (62/129) | 43% (55/129) | 45% (58/129) | 31% (40/129) | 15% (19/129) | 6% (8/129) |
| Qwen2.5-Coder-7B-Instruct | file | generic | 129 | 95% (122/129) | 60% (77/129) | 72% (93/129) | 50% (64/129) | 18% (23/129) | 20% (26/129) | 9% (11/129) | 16% (20/129) | 1% (1/129) |
| Qwen2.5-Coder-7B-Instruct | file | reuse | 129 | 91% (118/129) | 64% (83/129) | 68% (88/129) | 51% (66/129) | 22% (28/129) | 25% (32/129) | 9% (12/129) | 12% (15/129) | 3% (4/129) |
| Qwen2.5-Coder-7B-Instruct | none | generic | 129 | 98% (126/129) | 43% (55/129) | 78% (100/129) | 37% (48/129) | 1% (1/129) | 1% (1/129) | 0% (0/129) | 52% (67/129) | 1% (1/129) |
| Qwen2.5-Coder-7B-Instruct | none | reuse | 129 | 96% (124/129) | 40% (52/129) | 70% (90/129) | 33% (43/129) | 3% (4/129) | 5% (6/129) | 0% (0/129) | 58% (75/129) | 6% (8/129) |
| Qwen2.5-Coder-7B-Instruct | oracle | generic | 129 | 99% (128/129) | 49% (63/129) | 78% (100/129) | 43% (55/129) | 38% (49/129) | 38% (49/129) | 22% (28/129) | 30% (39/129) | 2% (2/129) |
| Qwen2.5-Coder-7B-Instruct | oracle | reuse | 129 | 98% (127/129) | 53% (68/129) | 80% (103/129) | 47% (60/129) | 53% (69/129) | 56% (72/129) | 36% (46/129) | 20% (26/129) | 6% (8/129) |


## Reuse funnel

Stages: helper in context → helper called (given in context) → tests pass (given called). Loss columns count tasks lost at each stage; the last column counts reuse without the helper in context (e.g. from training data).

| model | condition | instruction | helper in context | called (of in context) | pass (of called) | lost: not in context | lost: ignored | …of which reused another fn | lost: broken | called without context |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 76% (98/129) | 26% (25/98) | 80% (20/25) | 31 | 73 | 1 | 5 | 2 |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 76% (98/129) | 50% (49/98) | 82% (40/49) | 31 | 49 | 2 | 9 | 6 |
| Qwen2.5-Coder-7B-Instruct | file | generic | 62% (80/129) | 24% (19/80) | 63% (12/19) | 49 | 61 | 1 | 7 | 4 |
| Qwen2.5-Coder-7B-Instruct | file | reuse | 62% (80/129) | 30% (24/80) | 67% (16/24) | 49 | 56 | 3 | 8 | 4 |
| Qwen2.5-Coder-7B-Instruct | none | generic | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 1 |
| Qwen2.5-Coder-7B-Instruct | none | reuse | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 4 |
| Qwen2.5-Coder-7B-Instruct | oracle | generic | 100% (129/129) | 38% (49/129) | 69% (34/49) | 0 | 80 | 0 | 15 | 0 |
| Qwen2.5-Coder-7B-Instruct | oracle | reuse | 100% (129/129) | 53% (69/129) | 72% (50/69) | 0 | 60 | 3 | 19 | 0 |


## Retrieval of the helper (BM25)

| model | condition | instruction | n | recall@k | MRR |
|---|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | bm25 | generic | 129 | 76% (98/129) | 0.58 |
| Qwen2.5-Coder-7B-Instruct | bm25 | reuse | 129 | 76% (98/129) | 0.58 |
