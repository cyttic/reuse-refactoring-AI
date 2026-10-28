# Paper draft

ACL-format LaTeX (`acl.sty`, `acl_natbib.bst` from github.com/acl-org/acl-style-files, June 2026).

- `main.tex`: the paper; `main.pdf` is the compiled version. Compile on Overleaf (upload this folder),
  with `latexmk -pdf main.tex`, or without a local TeX installation:

      docker run --rm --network none -u $(id -u):$(id -g) -v "$PWD":/w -w /w texlive/texlive latexmk -pdf main.tex
- `references.bib`: entries downloaded from the ACL Anthology and arXiv.
- `tables/`: generated; do not edit by hand. After any re-run or re-evaluation:

      .venv/bin/python paper/make_tables.py

  It rewrites the table bodies and `tables/stats.json` (the numbers quoted in the text: check the text
  against it after a re-run).
