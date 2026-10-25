#!/usr/bin/env bash
# One-word entry point for the GPU server: pulls the latest code, starts the experiment inside tmux
# (so it survives a dropped connection) and pushes the results when it finishes.
#
#   ./run.sh                 list the experiments
#   ./run.sh position        run one of them
#   tmux attach -t position  reattach after a disconnect (detach again: Ctrl-b, then d)
#   tail -50 logs/position.log   what the run printed, even after the window closed
#   (a failed run pushes logs/ to GitHub by itself; bash scripts/push_logs.sh does it by hand)
set -euo pipefail
cd "$(dirname "$0")"

QWEN=Qwen/Qwen2.5-Coder-7B-Instruct
DEEPSEEK=deepseek-ai/deepseek-coder-6.7b-instruct
# 4-bit checkpoints of the 2025-26 models (bf16 does not fit the 24 GB A5000); need scripts/setup_vllm.sh
QWEN3_CODER=cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit
QWEN38=RedHatAI/Qwen3.8-27B-INT4
ALL_CONDITIONS=none,bm25,oracle,file,oracle_first,oracle_last

run() {     # run <model> <run name> [extra args for reuse_bench.generate]
    bash scripts/run_experiment.sh "$1" "$2" --backend hf "${@:3}"
}

run_vllm() {    # same, generating with vLLM from ~/env-vllm
    if [ ! -x "$HOME/env-vllm/bin/python" ]; then
        echo "vLLM environment missing: run ./run.sh setup-vllm first"
        return 1
    fi
    # The FlashInfer sampler JIT-compiles with nvcc, which this server lacks (vLLM's own sampler is used
    # instead); vLLM manages GPU memory itself, so the HF backend's allocator setting is left out.
    VLLM_USE_FLASHINFER_SAMPLER=0 PYTORCH_CUDA_ALLOC_CONF= GEN_PY=$HOME/env-vllm/bin/python \
        bash scripts/run_experiment.sh "$1" "$2" --backend vllm \
        --conditions "$ALL_CONDITIONS" --max-model-len 20480 --chunk 128 --gpu-memory-utilization 0.95 "${@:3}"
}

experiment() {
    case "$1" in
        qwen)     run "$QWEN" qwen7b-v1 ;;
        deepseek) run "$DEEPSEEK" deepseek67b-v1 ;;
        position)   # helper always first / always last among the oracle snippets, both models
            run "$QWEN" qwen7b-v1 --conditions oracle_first,oracle_last
            run "$DEEPSEEK" deepseek67b-v1 --conditions oracle_first,oracle_last ;;
        setup-vllm) bash scripts/setup_vllm.sh ;;
        qwen3coder) run_vllm "$QWEN3_CODER" qwen3coder30b-v1 ;;
        qwen38)     run_vllm "$QWEN38" qwen38-27b-v1 --no-thinking --text-only --enforce-eager ;;
        new-models) # both 2025-26 models, one after the other
            run_vllm "$QWEN3_CODER" qwen3coder30b-v1
            run_vllm "$QWEN38" qwen38-27b-v1 --no-thinking --text-only --enforce-eager ;;
        *) return 1 ;;
    esac
}

usage() {
    cat <<'EOF'
usage: ./run.sh <experiment>

  qwen       main conditions, Qwen2.5-Coder-7B        (~4-5 h)
  deepseek   main conditions, deepseek-coder-6.7b     (~4-5 h)
  position   helper first/last in the oracle context,
             both models                              (~2 h per model)

  setup-vllm  one-time: vLLM in ~/env-vllm (~/env stays untouched)
  qwen3coder  Qwen3-Coder-30B-A3B (4-bit), all six conditions, vLLM
  qwen38      Qwen3.8-27B (4-bit, thinking off), all six conditions, vLLM
  new-models  qwen3coder, then qwen38

Finished parts are skipped, so re-running the same experiment resumes it.
EOF
}

NAME=${1:-}
if [ -z "$NAME" ] || ! grep -q "^        $NAME)" "$0"; then
    usage
    exit 1
fi

if [ "${2:-}" != "--inside" ]; then
    # Update the code first, then start a fresh copy of this script in tmux.
    git pull --ff-only || echo "warning: git pull failed, running with local code"
    if tmux has-session -t "$NAME" 2>/dev/null; then
        echo "'$NAME' is already running; showing it (detach: Ctrl-b, then d)"
        exec tmux attach -t "$NAME"
    fi
    exec tmux new -s "$NAME" "bash ./run.sh $NAME --inside; echo; echo 'finished - press Enter to close'; read"
fi

# Keep everything this run prints, in case the tmux window is gone by the time you look.
mkdir -p logs
exec > >(tee -a "logs/$NAME.log") 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') starting '$NAME' (code $(git rev-parse --short HEAD))"
on_exit() {
    local code=$1
    echo "=== $(date "+%Y-%m-%d %H:%M:%S") stopped with exit code $code"
    # A failed run pushes nothing else; push the log so the error can be read on GitHub.
    [ "$code" -eq 0 ] || bash scripts/push_logs.sh || echo "could not push logs"
}
trap 'on_exit $?' EXIT
experiment "$NAME"
echo "experiment '$NAME' done"
