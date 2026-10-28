# Paper draft

ACL-format LaTeX (`acl.sty`, `acl_natbib.bst` from github.com/acl-org/acl-style-files, June 2026).

- `main.tex`: the paper. Compile on Overleaf (upload this folder) or with `latexmk -pdf main.tex`.
- `references.bib`: entries downloaded from the ACL Anthology and arXiv.
- `tables/`: generated; do not edit by hand. After any re-run or re-evaluation:

      .venv/bin/python paper/make_tables.py

  It rewrites the table bodies and `tables/stats.json` (the numbers quoted in the text: check the text
  against it after a re-run).
