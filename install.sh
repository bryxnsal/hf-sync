#!/usr/bin/env bash
# install.sh — install hf-sync (one-liner)
#   curl -fsSL https://raw.githubusercontent.com/bryxnsal/hf-sync/main/install.sh | bash
set -euo pipefail

REPO="bryxnsal/hf-sync"

# Get current version if already installed
CURRENT=""
if command -v hf-sync &>/dev/null; then
  CURRENT="$(hf-sync --version 2>/dev/null | sed 's/^hf-sync v//;s/[^0-9.]*//g' || true)"
fi

echo "==> hf-sync installer"

# Fetch latest release info
LATEST_JSON="$(curl -sfL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null || true)"
if [ -z "$LATEST_JSON" ]; then
  echo "✗ Failed to fetch latest release info from GitHub API"
  echo "  Check: curl -sfL https://api.github.com/repos/$REPO/releases/latest"
  exit 1
fi

TAG="$(echo "$LATEST_JSON" | grep '"tag_name":' | head -1 | sed 's/.*"tag_name": "//;s/".*//')"
if [ -z "$TAG" ]; then
  echo "✗ Could not find tag_name in response:"
  echo "$LATEST_JSON" | head -c 500
  echo
  exit 1
fi

VER="${TAG#v}"

# ---- uv (recommended) ----
if command -v uv &>/dev/null; then
  if [ -n "$CURRENT" ]; then
    echo "  Current: $CURRENT  →  New: $VER"
  else
    echo "  Version: $VER"
  fi

  echo "--> Installing via uv"
  uv tool install --reinstall --from "git+https://github.com/$REPO.git@$TAG" hf-sync --python 3.12 2>/dev/null || \
    uv tool install --from "git+https://github.com/$REPO.git@$TAG" hf-sync --python 3.12
  echo "✓ hf-sync installed ($VER)"
  hf-sync doctor 2>/dev/null || echo "  Run: hf-sync doctor"
  exit 0
fi

# ---- pip3 (fallback) ----
if command -v pip3 &>/dev/null; then
  if [ -n "$CURRENT" ]; then
    echo "  Current: $CURRENT  →  New: $VER"
  else
    echo "  Version: $VER"
  fi
  echo "--> Installing via pip3"
  pip3 install "git+https://github.com/$REPO.git@$TAG" 2>/dev/null || pip3 install "git+https://github.com/$REPO.git@$TAG"
  echo "✓ hf-sync installed ($VER)"
  hf-sync doctor 2>/dev/null || echo "  Run: hf-sync doctor"
  exit 0
fi

echo "✗ Need uv or pip3."
echo "  Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
exit 1
