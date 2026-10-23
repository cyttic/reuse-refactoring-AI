#!/usr/bin/env bash
# Install the GitHub CLI into ~/.local/bin without root (skipped if gh is already available).
set -euo pipefail

if command -v gh >/dev/null 2>&1 || [ -x "$HOME/.local/bin/gh" ]; then
    echo "gh already installed"; exit 0
fi
VERSION=$(curl -fsSL https://api.github.com/repos/cli/cli/releases/latest \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))')
case "$(uname -m)" in
    x86_64) ARCH=amd64 ;;
    aarch64|arm64) ARCH=arm64 ;;
    *) echo "unsupported architecture $(uname -m)"; exit 1 ;;
esac
TMP=$(mktemp -d)
curl -fsSL "https://github.com/cli/cli/releases/download/v${VERSION}/gh_${VERSION}_linux_${ARCH}.tar.gz" \
    | tar -xz -C "$TMP"
mkdir -p "$HOME/.local/bin"
mv "$TMP/gh_${VERSION}_linux_${ARCH}/bin/gh" "$HOME/.local/bin/gh"
rm -rf "$TMP"
echo "installed gh ${VERSION} to ~/.local/bin (add it to PATH: export PATH=\$HOME/.local/bin:\$PATH)"
