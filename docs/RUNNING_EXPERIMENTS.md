# Running the Experiments on the GPU Server — Step by Step

Code reaches the server with `git clone`; results come back with `git push`.
Nothing has to be copied, pasted or transferred by hand. All commands below are short enough to type.

```
 laptop (this project)  ──push code──▶  GitHub  ──clone/pull──▶  A5000 server
          ▲                                                              │
          └──────────── git pull ◀── GitHub ◀──── push results ──────────┘
```

**Short way (after the one-time setup below):**
```bash
cd ~/reuse-refactoring-AI
./run.sh             # lists the experiments
./run.sh position    # pulls the code, starts the experiment in tmux, pushes results at the end
```
If the connection drops, `tmux attach -t position` shows it again. Re-running the same command resumes.

---

## Part A — One-time preparation (on the laptop)

**A1. Create the GitHub repository.**
Open https://github.com/new → name `reuse-refactoring-AI` → **Public** → do *not* add a README,
.gitignore or license → *Create repository*.
(Private also works — see the note after B4.)

**A2. Push the code** (Claude does this once you confirm A1):
```bash
git add .gitignore README.md requirements*.txt reuse_bench tests scripts docs literature data
git commit -m "Benchmark builder and GPU experiment harness"
git remote add origin git@github.com:cyttic/reuse-refactoring-AI.git
git push -u origin main
```

---

## Part B — One-time setup (on the GPU server)

**B1. Open a tmux session** so long jobs survive a lost connection:
```bash
tmux new -s exp
```
(Detach: `Ctrl-b` then `d`. Re-attach later: `tmux attach -t exp`.)

**B2. Clone the repository:**
```bash
git clone https://github.com/cyttic/reuse-refactoring-AI.git
cd reuse-refactoring-AI
```

**B3. Install everything** (vLLM, the benchmark repositories, the GitHub CLI). Takes ~10–15 min:
```bash
bash scripts/server_setup.sh
```
- vLLM needs Python ≥ 3.10. If the default `python3` is older, choose another:
  `PYTHON=python3.11 bash scripts/server_setup.sh`
- The last lines must show the GPU and `cuda True`.

**B4. Allow the server to push results** (GitHub device login):
```bash
bash scripts/github_login.sh
```
1. Answer the questions if asked (GitHub.com → HTTPS → login with a web browser).
2. The server prints a code like `ABCD-1234` and says it cannot open a browser — that is expected.
3. On your laptop or phone open **https://github.com/login/device**, type the code, click *Authorize*.
4. The server prints `Logged in as cyttic`. The code is valid for 15 minutes; just re-run if it expires.

> **Private repository?** Then B2 cannot clone before logging in, and the login scripts live inside the
> repository. Simplest path: keep the repository public while setting up (B2–B4), then switch it to
> private in GitHub → Settings → Danger Zone. The server's login keeps working after the switch.

**B5. (Optional) Move the model cache** if the home directory is small (a 7B model ≈ 15 GB):
```bash
echo 'export HF_HOME=/path/to/big/disk/hf' >> ~/.bashrc && source ~/.bashrc
```

---

## Part C — Run an experiment (on the GPU server)

**C1. Smoke test** — 1 task, a few minutes, checks that vLLM, the tests and the push all work:
```bash
bash scripts/run_experiment.sh Qwen/Qwen2.5-Coder-7B-Instruct smoke --limit 1
```
At the end it prints a summary table and `pushed results/smoke`.

**C2. Pilot** — all current tasks × 4 conditions × 2 instructions:
```bash
bash scripts/run_experiment.sh Qwen/Qwen2.5-Coder-7B-Instruct qwen7b-pilot
```

**C3. More models** — one run name per model:

| Model | Command |
|-------|---------|
| Qwen2.5-Coder 7B | `bash scripts/run_experiment.sh Qwen/Qwen2.5-Coder-7B-Instruct qwen7b` |
| Qwen2.5-Coder 14B (4-bit) | `bash scripts/run_experiment.sh Qwen/Qwen2.5-Coder-14B-Instruct-AWQ qwen14b` |
| Qwen2.5-Coder 32B (4-bit) | `bash scripts/run_experiment.sh Qwen/Qwen2.5-Coder-32B-Instruct-AWQ qwen32b --max-model-len 12288 --max-file-chars 20000` |
| DeepSeek-Coder 6.7B | `bash scripts/run_experiment.sh deepseek-ai/deepseek-coder-6.7b-instruct deepseek67b --no-system-prompt` |

What each run does automatically:
1. `git pull` — always uses the newest code and tasks.
2. Downloads the benchmark repositories at their pinned commits.
3. **Generate** (GPU): builds the prompts and runs the model → `generations.jsonl`.
4. **Evaluate** (CPU): applies every answer, runs the repository tests, checks if the helper is reused → `metrics.jsonl`.
5. **Summarize** → `summary.md`.
6. **Push** `results/<run>/` to GitHub.

**C4. Watch progress** (from another tmux window, `Ctrl-b c`):
```bash
tail -f results/qwen7b-pilot/generate.log
tail -f results/qwen7b-pilot/evaluate.log
nvidia-smi
```

**C5. If something stops** (disconnect, crash, out of memory): run **the same command again**.
Finished prompts and evaluations are skipped.

---

## Part D — Get the results (on the laptop)

```bash
git pull
cat results/qwen7b-pilot/summary.md
```
Or just tell Claude "results for qwen7b-pilot are pushed" — it pulls and analyzes them.

Files in `results/<run>/`:

| File | Content |
|------|---------|
| `run_info.json` | model, GPU, code commit, start time |
| `generations.jsonl` | one line per prompt: condition, instruction, what was retrieved, raw model output |
| `metrics.jsonl` | one line per output: applied?, tests pass?, helper reused?, new helpers defined, signature kept |
| `summary.md` | table per model × condition × instruction |
| `*.tail.txt` | last 300 lines of the logs (for debugging) |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `pip install vllm` fails (CUDA / driver mismatch) | `.venv/bin/pip install torch transformers accelerate`, then add `--backend hf` to the run command (slower) |
| `CUDA out of memory` / "max seq len larger than KV cache" | add `--max-model-len 8192 --max-file-chars 15000` |
| Model download very slow or disk full | set `HF_HOME` (B5) |
| Chat template error mentioning "system" | add `--no-system-prompt` |
| `git push` rejected / authentication failed | `bash scripts/github_login.sh`, then `bash scripts/push_results.sh results/<run>` |
| `git pull` conflict at the start of a run | `git stash && git pull` (results are committed, so nothing is lost) |
| Run finished but you want to re-push | `bash scripts/push_results.sh results/<run>` |
| Want to start a run from scratch | delete it: `rm -rf results/<run>` (and push), or use a new run name |
