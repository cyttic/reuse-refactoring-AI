# Reuse-Oriented Refactoring with LLMs

Course project 10 (Code Reuse / Refactoring with AI): do LLMs **reuse existing project helpers** when they
refactor code, and does **repository retrieval** help? Design: [docs/experiment_design.md](docs/experiment_design.md) ·
literature: [literature/literature_review.md](literature/literature_review.md).

## Layout

| Path | What |
|------|------|
| `reuse_bench/build.py` | Builds tasks: inlines a helper `H` into its caller `F`, keeps it if tests cover and still pass |
| `reuse_bench/generate.py` | GPU stage: prompts × conditions (`none`, `bm25`, `oracle`, `file`) × instructions (`generic`, `reuse`) via vLLM |
| `reuse_bench/evaluate.py` | CPU stage: applies each output, runs the repo's tests, checks whether `H` is called |
| `reuse_bench/summarize.py` | Markdown table per model / condition / instruction |
| `data/tasks/*.jsonl` | Benchmark tasks (patches against pinned commits) |
| `data/repos.json` | Benchmark repositories, pinned commits, pytest arguments |
| `results/<run>/` | Pushed back from the GPU server: `generations.jsonl`, `metrics.jsonl`, `summary.md` |

## Running on the GPU server

Full step-by-step guide with troubleshooting: [docs/RUNNING_EXPERIMENTS.md](docs/RUNNING_EXPERIMENTS.md).
No copy-paste or file transfer is needed: code comes in with `git clone`, results go out with `git push`.

```bash
# 1. once: get the code and install everything (vLLM, benchmark repos, GitHub CLI)
git clone https://github.com/cyttic/reuse-refactoring-AI.git
cd reuse-refactoring-AI
bash scripts/server_setup.sh            # PYTHON=python3.12 bash scripts/server_setup.sh to choose Python

# 2. once: allow the server to push results
bash scripts/github_login.sh
#    -> prints a code like ABCD-1234; on your laptop/phone open https://github.com/login/device,
#       type the code and approve. Nothing has to be copied from the server.

# 3. each experiment (inside tmux so it survives disconnects: `tmux new -s exp`, detach Ctrl-b d)
bash scripts/run_experiment.sh Qwen/Qwen2.5-Coder-7B-Instruct qwen7b-pilot
```

`run_experiment.sh` pulls the latest code, generates, evaluates, writes `results/<run>/summary.md`
and pushes. Re-running the same command resumes where it stopped. To push manually:
`bash scripts/push_results.sh results/<run>`.

Models that fit the A5000 (24 GB):

| Model | Command | Notes |
|-------|---------|-------|
| Qwen2.5-Coder-7B-Instruct | `run_experiment.sh Qwen/Qwen2.5-Coder-7B-Instruct qwen7b` | bf16, fits easily |
| Qwen2.5-Coder-14B-Instruct (AWQ) | `run_experiment.sh Qwen/Qwen2.5-Coder-14B-Instruct-AWQ qwen14b` | 4-bit |
| Qwen2.5-Coder-32B-Instruct (AWQ) | `run_experiment.sh Qwen/Qwen2.5-Coder-32B-Instruct-AWQ qwen32b --max-model-len 12288 --max-file-chars 20000` | tight on 24 GB |
| DeepSeek-Coder-6.7B-Instruct | `run_experiment.sh deepseek-ai/deepseek-coder-6.7b-instruct deepseek67b --no-system-prompt` | |

Any Hugging Face model id works; extra arguments go to `reuse_bench.generate` (see `--help`).
Set `HF_HOME=/path/with/space` if the home directory is small. If vLLM cannot be installed, add `--backend hf`.

## Local development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests
.venv/bin/python -m reuse_bench.build data/repos/boltons --out data/tasks/boltons.jsonl --pytest-args "-x -q tests"
```
