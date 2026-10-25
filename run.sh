#!/usr/bin/env bash
# One-word entry point for the GPU server: pulls the latest code, starts the experiment inside tmux
# (so it survives a dropped connection) and pushes the results when it finishes.
#
#   ./run.sh                 list the experiments
#   ./run.sh position        run one of them
#   tmux attach -t position  reattach after a disconnect (detach again: Ctrl-b, then d)
#   tail -50 logs/position.log   what the run printed, even after the window closed
set -euo pipefail
cd "$(dirname "$0")"

QWEN=Qwen/Qwen2.5-Coder-7B-Instruct
DEEPSEEK=deepseek-ai/deepseek-coder-6.7b-instruct

run() {     # run <model> <run name> [extra args for reuse_bench.generate]
    bash scripts/run_experiment.sh "$1" "$2" --backend hf "${@:3}"
}

experiment() {
    case "$1" in
        qwen)     run "$QWEN" qwen7b-v1 ;;
        deepseek) run "$DEEPSEEK" deepseek67b-v1 ;;
        position)   # helper always first / always last among the oracle snippets, both models
            run "$QWEN" qwen7b-v1 --conditions oracle_first,oracle_last
            run "$DEEPSEEK" deepseek67b-v1 --conditions oracle_first,oracle_last ;;
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
trap 'echo "=== $(date "+%Y-%m-%d %H:%M:%S") stopped with exit code $?"' EXIT
experiment "$NAME"
echo "experiment '$NAME' done"
