#!/usr/bin/env bash
# Generate (GPU) -> evaluate (CPU, runs repo tests) -> summarize -> push results to GitHub.
#   bash scripts/run_experiment.sh Qwen/Qwen2.5-Coder-7B-Instruct qwen7b-pilot [extra reuse_bench.generate args]
# Resumable: re-running with the same run name skips finished prompts and evaluations.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True   # less fragmentation on long prompts
export PYTHONUNBUFFERED=1   # otherwise progress lines sit in a buffer when piped through tee

MODEL=${1:?usage: $0 MODEL RUN_NAME [extra args for reuse_bench.generate]}
RUN=${2:?usage: $0 MODEL RUN_NAME [extra args for reuse_bench.generate]}
shift 2
OUT=results/$RUN
PY=.venv/bin/python
mkdir -p "$OUT"

git pull --ff-only || echo "warning: git pull failed, running with local code"
$PY -m reuse_bench.fetch_repos

$PY - "$OUT/run_info.json" "$MODEL" "$RUN" "$*" <<'EOF'
import json, subprocess, sys, time
path, model, run, extra = sys.argv[1:]
gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                     capture_output=True, text=True).stdout.strip()
commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
info = {"run": run, "model": model, "extra_args": extra, "gpu": gpu, "code_commit": commit,
        "started": time.strftime("%Y-%m-%d %H:%M:%S")}
try:    # resuming / extending a run: keep the first run's info, list later ones under "continued"
    first = json.load(open(path))
except (OSError, ValueError):
    first = None
if first:
    if first["model"] != model:
        sys.exit(f"ERROR: {path} belongs to {first['model']}; use a new run name for {model}")
    info = {**first, "continued": first.get("continued", []) + [info]}
json.dump(info, open(path, "w"), indent=2)
EOF

$PY -m reuse_bench.generate --tasks data/tasks/*.jsonl --model "$MODEL" \
    --out "$OUT/generations.jsonl" "$@" 2>&1 | tee -a "$OUT/generate.log"
$PY -m reuse_bench.evaluate --tasks data/tasks/*.jsonl --generations "$OUT/generations.jsonl" \
    --out "$OUT/metrics.jsonl" 2>&1 | tee -a "$OUT/evaluate.log"
$PY -m reuse_bench.summarize "$OUT/metrics.jsonl" --out "$OUT/summary.md"

bash scripts/push_results.sh "$OUT"
