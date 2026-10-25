#!/usr/bin/env bash
# One-time: a separate Python environment with vLLM for the larger (4-bit) models.
# ~/env is not touched: vLLM pins its own torch version, which would replace the one there.
#   bash scripts/setup_vllm.sh
set -euo pipefail
cd "$(dirname "$0")/.."

VLLM_VERSION=0.32.0
ENV=$HOME/env-vllm
# The interpreter behind .venv (-> ~/env) is known to work on this machine and has the venv module.
BASE_PY=$(.venv/bin/python -c 'import sys; print(sys._base_executable)')

echo "free disk space (vLLM ~6 GB, each model ~20 GB in ~/.cache/huggingface):"
df -h "$HOME" | tail -1

[ -d "$ENV" ] || "$BASE_PY" -m venv "$ENV"
"$ENV/bin/pip" install -q --upgrade pip
"$ENV/bin/pip" install "vllm==$VLLM_VERSION"

"$ENV/bin/python" -c "import torch, vllm; print('vllm', vllm.__version__, '| torch', torch.__version__, '| cuda', torch.cuda.is_available())"
echo
echo "vLLM environment ready: $ENV"
