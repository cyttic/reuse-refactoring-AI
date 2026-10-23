#!/usr/bin/env bash
# One-time setup on the GPU server: Python venv with vLLM, benchmark repositories, GitHub CLI.
#   PYTHON=python3.12 bash scripts/server_setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON=${PYTHON:-python3}
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 10), "need Python >= 3.10, got " + sys.version'

[ -d .venv ] || "$PYTHON" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -r requirements-gpu.txt

.venv/bin/python -m reuse_bench.fetch_repos
bash scripts/install_gh.sh

nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
.venv/bin/python -c "import torch, vllm; print('vllm', vllm.__version__, '| torch', torch.__version__, '| cuda', torch.cuda.is_available())"
echo
echo "Setup done. Next: bash scripts/github_login.sh (once), then bash scripts/run_experiment.sh <model> <run-name>"
