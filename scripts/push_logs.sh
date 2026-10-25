#!/usr/bin/env bash
# Commit logs/ (normally git-ignored) and push it, so a failed run can be diagnosed from GitHub.
#   bash scripts/push_logs.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

git add -f logs
git commit -q -m "Logs ($(hostname))" || echo "logs unchanged"
git pull -q --rebase --autostash
git push -q
echo "pushed logs/"
