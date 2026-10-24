## Overall

*compliant*: signature kept and no existing code redefined (violations are dropped before testing); *valid*: tests pass and compliant; *reuses any*: calls the target helper or another repository function the input did not call (check these by hand).

| model | condition | instruction | n | applied | tests pass | compliant | valid | reuses helper | reuses any | valid & reuses helper | defines new helper | hallucinated import |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-coder-6.7b-instruct | bm25 | generic | 129 | 91% (117/129) | 57% (74/129) | 69% (89/129) | 45% (58/129) | 33% (42/129) | 33% (42/129) | 19% (25/129) | 30% (39/129) | 1% (1/129) |
| deepseek-coder-6.7b-instruct | bm25 | reuse | 129 | 97% (125/129) | 55% (71/129) | 72% (93/129) | 45% (58/129) | 47% (60/129) | 47% (61/129) | 24% (31/129) | 36% (46/129) | 2% (3/129) |
| deepseek-coder-6.7b-instruct | file | generic | 129 | 84% (108/129) | 65% (84/129) | 53% (68/129) | 47% (60/129) | 18% (23/129) | 19% (25/129) | 9% (12/129) | 16% (20/129) | 1% (1/129) |
| deepseek-coder-6.7b-instruct | file | reuse | 129 | 84% (108/129) | 63% (81/129) | 53% (69/129) | 43% (55/129) | 19% (24/129) | 21% (27/129) | 10% (13/129) | 18% (23/129) | 1% (1/129) |
| deepseek-coder-6.7b-instruct | none | generic | 129 | 88% (114/129) | 45% (58/129) | 63% (81/129) | 36% (46/129) | 4% (5/129) | 4% (5/129) | 0% (0/129) | 48% (62/129) | 1% (1/129) |
| deepseek-coder-6.7b-instruct | none | reuse | 129 | 89% (115/129) | 46% (59/129) | 64% (83/129) | 37% (48/129) | 5% (7/129) | 5% (7/129) | 1% (1/129) | 49% (63/129) | 1% (1/129) |
| deepseek-coder-6.7b-instruct | oracle | generic | 129 | 96% (124/129) | 55% (71/129) | 72% (93/129) | 42% (54/129) | 36% (46/129) | 36% (47/129) | 18% (23/129) | 36% (46/129) | 2% (2/129) |
| deepseek-coder-6.7b-instruct | oracle | reuse | 129 | 96% (124/129) | 53% (68/129) | 72% (93/129) | 42% (54/129) | 45% (58/129) | 47% (60/129) | 24% (31/129) | 40% (51/129) | 2% (3/129) |


## Reuse funnel

Stages: helper in context → helper called (given in context) → tests pass (given called). Loss columns count tasks lost at each stage; the last column counts reuse without the helper in context (e.g. from training data).

| model | condition | instruction | helper in context | called (of in context) | pass (of called) | lost: not in context | lost: ignored | …of which reused another fn | lost: broken | called without context |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek-coder-6.7b-instruct | bm25 | generic | 76% (98/129) | 39% (38/98) | 66% (25/38) | 31 | 60 | 0 | 13 | 4 |
| deepseek-coder-6.7b-instruct | bm25 | reuse | 76% (98/129) | 58% (57/98) | 63% (36/57) | 31 | 41 | 1 | 21 | 3 |
| deepseek-coder-6.7b-instruct | file | generic | 62% (80/129) | 28% (22/80) | 86% (19/22) | 49 | 58 | 1 | 3 | 1 |
| deepseek-coder-6.7b-instruct | file | reuse | 62% (80/129) | 28% (22/80) | 91% (20/22) | 49 | 58 | 1 | 2 | 2 |
| deepseek-coder-6.7b-instruct | none | generic | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 5 |
| deepseek-coder-6.7b-instruct | none | reuse | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 7 |
| deepseek-coder-6.7b-instruct | oracle | generic | 100% (129/129) | 36% (46/129) | 59% (27/46) | 0 | 83 | 1 | 19 | 0 |
| deepseek-coder-6.7b-instruct | oracle | reuse | 100% (129/129) | 45% (58/129) | 64% (37/58) | 0 | 71 | 2 | 21 | 0 |


## Retrieval of the helper (BM25)

| model | condition | instruction | n | recall@k | MRR |
|---|---|---|---|---|---|
| deepseek-coder-6.7b-instruct | bm25 | generic | 129 | 76% (98/129) | 0.58 |
| deepseek-coder-6.7b-instruct | bm25 | reuse | 129 | 76% (98/129) | 0.58 |
