#!/usr/bin/env bash
# install.sh — install hf-sync (one-liner)
#   curl -fsSL https://raw.githubusercontent.com/bryxnsal/hf-sync/main/install.sh | bash
set -euo pipefail

REPO="bryxnsal/hf-sync"
BRANCH="${1:-main}"

# Detect if already installed (for messaging)
if command -v hf-sync &>/dev/null; then
  ACTION="Updating"
  DONE="✓ hf-sync updated"
else
  ACTION="Installing"
  DONE="✓ hf-sync installed"
fi

echo "==> hf-sync installer"

# ---- uv (recommended) ----
if command -v uv &>/dev/null; then
  echo "--> $ACTION via uv"
  tmp="$(mktemp -d)"
  git clone --depth 1 --branch "$BRANCH" "https://github.com/$REPO.git" "$tmp" 2>/dev/null || {
    echo "✗ Failed to clone repo. Check branch name and network."
    rm -rf "$tmp"
    exit 1
  }
  uv tool install --reinstall "$tmp" --python 3.12 2>/dev/null || uv tool install "$tmp" --python 3.12
  rm -rf "$tmp"
  echo "$DONE"
  hf-sync doctor 2>/dev/null || echo "  Run: hf-sync doctor"
  exit 0
fi

# ---- pip3 (fallback) ----
if command -v pip3 &>/dev/null; then
  echo "--> $ACTION via pip3"
  pip3 install "git+https://github.com/$REPO.git@$BRANCH"
  echo "$DONE"
  hf-sync doctor 2>/dev/null || echo "  Run: hf-sync doctor"
  exit 0
fi

echo "✗ Need uv or pip3."
echo "  Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
exit 1
