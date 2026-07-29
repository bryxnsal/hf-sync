#!/usr/bin/env bash
# install.sh — install hf-sync (one-liner)
#   curl -fsSL https://raw.githubusercontent.com/bryxnsal/hf-sync/main/install.sh | bash
set -euo pipefail

REPO="bryxnsal/hf-sync"
BRANCH="${1:-main}"

# Get current version if already installed
CURRENT=""
if command -v hf-sync &>/dev/null; then
  CURRENT="$(hf-sync --version 2>/dev/null | sed 's/^hf-sync v//;s/[^0-9.]//g' || true)"
fi

echo "==> hf-sync installer"

# ---- uv (recommended) ----
if command -v uv &>/dev/null; then
  echo "--> Installing via uv"
  tmp="$(mktemp -d)"
  git clone --depth 1 --branch "$BRANCH" "https://github.com/$REPO.git" "$tmp" 2>/dev/null || {
    echo "✗ Failed to clone repo. Check branch name and network."
    rm -rf "$tmp"
    exit 1
  }
  NEW_VER="$(cd "$tmp" && git tag --points-at HEAD 2>/dev/null | head -1 | sed 's/^v//')"
  [ -z "$NEW_VER" ] && NEW_VER="dev ($BRANCH)"

  if [ -n "$CURRENT" ]; then
    echo "  Current: $CURRENT  →  New: $NEW_VER"
  else
    echo "  Version: $NEW_VER"
  fi

  uv tool install --reinstall "$tmp" --python 3.12 2>/dev/null || uv tool install "$tmp" --python 3.12
  rm -rf "$tmp"
  echo "✓ hf-sync installed ($NEW_VER)"
  hf-sync doctor 2>/dev/null || echo "  Run: hf-sync doctor"
  exit 0
fi

# ---- pip3 (fallback) ----
if command -v pip3 &>/dev/null; then
  NEW_VER="dev ($BRANCH)"
  if [ -n "$CURRENT" ]; then
    echo "  Current: $CURRENT  →  New: $NEW_VER"
  else
    echo "  Version: $NEW_VER"
  fi
  echo "--> Installing via pip3"
  pip3 install "git+https://github.com/$REPO.git@$BRANCH"
  echo "✓ hf-sync installed ($NEW_VER)"
  hf-sync doctor 2>/dev/null || echo "  Run: hf-sync doctor"
  exit 0
fi

echo "✗ Need uv or pip3."
echo "  Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
exit 1
