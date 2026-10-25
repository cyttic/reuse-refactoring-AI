#!/usr/bin/env bash
# Commit a results directory and push it to GitHub (needs scripts/github_login.sh once).
#   bash scripts/push_results.sh results/<run>
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

DIR=${1:?usage: $0 results/<run>}
# Full logs (vLLM progress bars) are large and git-ignored; keep only their tails.
for log in "$DIR"/*.log; do
    [ -f "$log" ] && tail -n 300 "$log" > "${log%.log}.tail.txt"
done

git add "$DIR"
git commit -q -m "Results: $(basename "$DIR") ($(hostname))" || echo "nothing new to commit"
git pull -q --rebase --autostash   # other uncommitted files must not block the push
git push -q
echo "pushed $DIR"
