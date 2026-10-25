## Overall

*compliant*: signature kept and no existing code redefined (violations are dropped before testing); *valid*: tests pass and compliant; *reuses any*: calls the target helper or another repository function the input did not call (check these by hand).

| model | condition | instruction | n | applied | tests pass | compliant | valid | reuses helper | reuses any | valid & reuses helper | defines new helper | hallucinated import |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | generic | 129 | 98% (127/129) | 91% (118/129) | 95% (123/129) | 91% (117/129) | 22% (28/129) | 22% (29/129) | 22% (28/129) | 2% (2/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | reuse | 129 | 98% (126/129) | 88% (113/129) | 95% (122/129) | 87% (112/129) | 41% (53/129) | 43% (56/129) | 38% (49/129) | 0% (0/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | generic | 129 | 98% (127/129) | 94% (121/129) | 98% (126/129) | 93% (120/129) | 9% (12/129) | 10% (13/129) | 9% (12/129) | 1% (1/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | reuse | 129 | 96% (124/129) | 90% (116/129) | 95% (122/129) | 88% (114/129) | 27% (35/129) | 29% (38/129) | 27% (35/129) | 2% (2/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | generic | 129 | 98% (127/129) | 91% (117/129) | 98% (127/129) | 91% (117/129) | 2% (3/129) | 2% (3/129) | 2% (2/129) | 16% (20/129) | 3% (4/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | reuse | 129 | 97% (125/129) | 91% (117/129) | 96% (124/129) | 90% (116/129) | 5% (7/129) | 5% (7/129) | 5% (6/129) | 14% (18/129) | 4% (5/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | generic | 129 | 98% (127/129) | 88% (114/129) | 95% (123/129) | 88% (113/129) | 19% (24/129) | 20% (26/129) | 19% (24/129) | 3% (4/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | reuse | 129 | 98% (126/129) | 84% (108/129) | 94% (121/129) | 83% (107/129) | 54% (70/129) | 57% (74/129) | 51% (66/129) | 0% (0/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_first | generic | 129 | 98% (127/129) | 91% (118/129) | 96% (124/129) | 91% (117/129) | 29% (37/129) | 29% (38/129) | 26% (34/129) | 2% (3/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_first | reuse | 129 | 98% (126/129) | 88% (113/129) | 95% (123/129) | 86% (111/129) | 54% (70/129) | 57% (73/129) | 52% (67/129) | 0% (0/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_last | generic | 129 | 98% (127/129) | 88% (114/129) | 95% (123/129) | 88% (113/129) | 19% (25/129) | 21% (27/129) | 19% (24/129) | 2% (2/129) | 0% (0/129) |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_last | reuse | 129 | 98% (126/129) | 86% (111/129) | 95% (122/129) | 85% (110/129) | 51% (66/129) | 55% (71/129) | 50% (65/129) | 1% (1/129) | 0% (0/129) |


## Reuse funnel

Stages: helper in context → helper called (given in context) → tests pass (given called). Loss columns count tasks lost at each stage; the last column counts reuse without the helper in context (e.g. from training data).

| model | condition | instruction | helper in context | called (of in context) | pass (of called) | lost: not in context | lost: ignored | …of which reused another fn | lost: broken | called without context |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | generic | 76% (98/129) | 26% (25/98) | 100% (25/25) | 31 | 73 | 0 | 0 | 3 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | reuse | 76% (98/129) | 49% (48/98) | 92% (44/48) | 31 | 50 | 2 | 4 | 5 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | generic | 62% (80/129) | 14% (11/80) | 100% (11/11) | 49 | 69 | 0 | 0 | 1 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | file | reuse | 62% (80/129) | 38% (30/80) | 100% (30/30) | 49 | 50 | 0 | 0 | 5 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | generic | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 3 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | none | reuse | 0% (0/129) | – | – | 129 | 0 | 0 | 0 | 7 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | generic | 100% (129/129) | 19% (24/129) | 100% (24/24) | 0 | 105 | 2 | 0 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle | reuse | 100% (129/129) | 54% (70/129) | 94% (66/70) | 0 | 59 | 4 | 4 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_first | generic | 100% (129/129) | 29% (37/129) | 92% (34/37) | 0 | 92 | 1 | 3 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_first | reuse | 100% (129/129) | 54% (70/129) | 96% (67/70) | 0 | 59 | 3 | 3 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_last | generic | 100% (129/129) | 19% (25/129) | 96% (24/25) | 0 | 104 | 2 | 1 | 0 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | oracle_last | reuse | 100% (129/129) | 51% (66/129) | 98% (65/66) | 0 | 63 | 5 | 1 | 0 |


## Retrieval of the helper (BM25)

| model | condition | instruction | n | recall@k | MRR |
|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | generic | 129 | 76% (98/129) | 0.58 |
| Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit | bm25 | reuse | 129 | 76% (98/129) | 0.58 |
