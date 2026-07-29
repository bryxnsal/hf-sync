#!/usr/bin/env bash
# uninstall.sh — uninstall hf-sync
#   curl -fsSL https://raw.githubusercontent.com/bryxnsal/hf-sync/main/uninstall.sh | bash
set -euo pipefail

echo "==> hf-sync uninstaller"

FOUND=0

# ---- Remove binary ----
if command -v uv &>/dev/null && uv tool list 2>/dev/null | grep -q hf-sync; then
  echo "--> Removing via uv..."
  uv tool uninstall hf-sync
  FOUND=1
fi

if pip3 show hf-sync &>/dev/null 2>&1; then
  echo "--> Removing via pip3..."
  pip3 uninstall hf-sync -y
  FOUND=1
fi

if pip show hf-sync &>/dev/null 2>&1; then
  echo "--> Removing via pip..."
  pip uninstall hf-sync -y
  FOUND=1
fi

# ---- Clean temp files (always) ----
rm -rf /tmp/hf-sync* "$TMPDIR/hf-sync"* 2>/dev/null || true
echo "✓ Temp files cleaned"

# ---- Ask about user data (DB) ----
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/hf-sync"
if [ -d "$DATA_DIR" ]; then
  echo ""
  echo "User data found at: $DATA_DIR"
  echo "  Contains: sync DB, config, logs"
  read -r -p "Delete user data? [y/N] " REPLY
  if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    rm -rf "$DATA_DIR"
    echo "✓ User data deleted"
  else
    echo "  Skipped — data kept at $DATA_DIR"
  fi
fi

if [ "$FOUND" -eq 0 ]; then
  echo "✗ hf-sync binary not found (already uninstalled?)"
  exit 1
fi

echo ""
echo "✓ hf-sync uninstalled"
