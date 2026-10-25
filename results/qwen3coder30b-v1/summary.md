## Overall

*compliant*: signature kept and no existing code redefined (violations are dropped before testing); *valid*: tests pass and compliant; *reuses any*: calls the target helper or another repository function the input did not call (check these by hand).

| model | condition | instruction | n | applied | tests pass | compliant | valid | reuses helper | reuses any | valid & reuses helper | defines new helper | hallucinated import |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | generic | 129 | 97% (125/129) | 90% (116/129) | 94% (121/129) | 89% (115/129) | 22% (28/129) | 22% (29/129) | 22% (28/129) | 1% (1/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | reuse | 129 | 98% (126/129) | 88% (113/129) | 95% (122/129) | 87% (112/129) | 41% (53/129) | 43% (56/129) | 38% (49/129) | 0% (0/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | generic | 129 | 93% (120/129) | 88% (114/129) | 92% (119/129) | 88% (113/129) | 9% (11/129) | 9% (12/129) | 9% (11/129) | 1% (1/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | reuse | 129 | 86% (111/129) | 81% (104/129) | 84% (109/129) | 79% (102/129) | 25% (32/129) | 27% (35/129) | 25% (32/129) | 1% (1/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | generic | 129 | 91% (118/129) | 84% (109/129) | 91% (118/129) | 84% (109/129) | 2% (3/129) | 2% (3/129) | 2% (2/129) | 15% (19/129) | 3% (4/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | reuse | 129 | 93% (120/129) | 87% (112/129) | 92% (119/129) | 86% (111/129) | 5% (6/129) | 5% (6/129) | 4% (5/129) | 13% (17/129) | 4% (5/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | generic | 129 | 95% (122/129) | 84% (109/129) | 91% (118/129) | 84% (108/129) | 19% (24/129) | 20% (26/129) | 19% (24/129) | 2% (3/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | reuse | 129 | 96% (124/129) | 82% (106/129) | 92% (119/129) | 81% (105/129) | 53% (68/129) | 56% (72/129) | 50% (64/129) | 0% (0/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_first | generic | 129 | 96% (124/129) | 89% (115/129) | 94% (121/129) | 88% (114/129) | 29% (37/129) | 29% (38/129) | 26% (34/129) | 2% (2/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_first | reuse | 129 | 95% (122/129) | 85% (110/129) | 92% (119/129) | 84% (108/129) | 52% (67/129) | 54% (70/129) | 50% (64/129) | 0% (0/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_last | generic | 129 | 95% (123/129) | 85% (110/129) | 92% (119/129) | 84% (109/129) | 19% (25/129) | 21% (27/129) | 19% (24/129) | 0% (0/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_last | reuse | 129 | 98% (126/129) | 86% (111/129) | 95% (122/129) | 85% (110/129) | 51% (66/129) | 55% (71/129) | 50% (65/129) | 1% (1/129) | 0% (0/129) |


## Reuse funnel

Stages: helper in context → helper called (given in context) → tests pass (given called). Loss columns count tasks lost at each stage; the last column counts reuse without the helper in context (e.g. from training data).

| model | condition | instruction | helper in context | called (of in context) | pass (of called) | lost: not in context | lost: ignored | …of which reused another fn | lost: broken | called without context |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | generic | 76% (98/129) | 26% (25/98) | 100% (25/25) | 31 | 73 | 0 | 0 | 3 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | reuse | 76% (98/129) | 49% (48/98) | 92% (44/48) | 31 | 50 | 2 | 4 | 5 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | generic | 62% (80/129) | 12% (10/80) | 100% (10/10) | 49 | 70 | 0 | 0 | 1 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | reuse | 62% (80/129) | 34% (27/80) | 100% (27/27) | 49 | 53 | 0 | 0 | 5 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | generic | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 3 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | reuse | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 6 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | generic | 100% (129/129) | 19% (24/129) | 100% (24/24) | 0 | 105 | 2 | 0 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | reuse | 100% (129/129) | 53% (68/129) | 94% (64/68) | 0 | 61 | 4 | 4 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_first | generic | 100% (129/129) | 29% (37/129) | 92% (34/37) | 0 | 92 | 1 | 3 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_first | reuse | 100% (129/129) | 52% (67/129) | 96% (64/67) | 0 | 62 | 3 | 3 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_last | generic | 100% (129/129) | 19% (25/129) | 96% (24/25) | 0 | 104 | 2 | 1 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_last | reuse | 100% (129/129) | 51% (66/129) | 98% (65/66) | 0 | 63 | 5 | 1 | 0 |


## Retrieval of the helper (BM25)

| model | condition | instruction | n | recall@k | MRR |
|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | generic | 129 | 76% (98/129) | 0.58 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | reuse | 129 | 76% (98/129) | 0.58 |
