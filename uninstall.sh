#!/usr/bin/env bash
# uninstall.sh — uninstall hf-sync
#   curl -fsSL https://raw.githubusercontent.com/bryxnsal/hf-sync/main/uninstall.sh | bash
set -euo pipefail

echo "==> hf-sync uninstaller"

FOUND=0

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

# Also check pip (py -3 -m pip on Windows, but this is Linux)
if pip show hf-sync &>/dev/null 2>&1; then
  echo "--> Removing via pip..."
  pip uninstall hf-sync -y
  FOUND=1
fi

if [ "$FOUND" -eq 0 ]; then
  echo "✗ hf-sync not found"
  exit 1
fi

echo "✓ hf-sync uninstalled"
