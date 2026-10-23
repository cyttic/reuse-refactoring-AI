#!/usr/bin/env bash
# Log the server into GitHub without copy-paste: it prints an 8-character code; open
# https://github.com/login/device on any other device, type the code and approve.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

gh auth status >/dev/null 2>&1 || gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git   # lets `git push` use the gh login

if ! git config user.email >/dev/null; then
    LOGIN=$(gh api user --jq .login)
    git config user.name "$LOGIN"
    git config user.email "$(gh api user --jq .id)+${LOGIN}@users.noreply.github.com"
fi
echo "Logged in as $(gh api user --jq .login); results can now be pushed."
