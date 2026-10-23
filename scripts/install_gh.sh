#!/usr/bin/env bash
# Install the GitHub CLI into ~/.local/bin without root (skipped if gh is already available).
set -euo pipefail

if command -v gh >/dev/null 2>&1 || [ -x "$HOME/.local/bin/gh" ]; then
    echo "gh already installed"; exit 0
fi
# The "latest" release page redirects to .../tag/v<version>; no API call or JSON parsing needed.
LATEST=$(curl -fsSLI -o /dev/null -w '%{url_effective}' https://github.com/cli/cli/releases/latest)
VERSION=${LATEST##*/v}
[ -n "$VERSION" ] && [ "$VERSION" != "$LATEST" ] || { echo "could not determine gh version from $LATEST"; exit 1; }
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
