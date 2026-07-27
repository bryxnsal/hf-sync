#!/usr/bin/env bash
# Check system dependencies and configuration
set -euo pipefail

echo "=== HF Sync Doctor ===

check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo "  ✓ $1 found: $(command -v "$1")"
    else
        echo "  ✗ $1 NOT found"
    fi
}

echo "--- Dependencies ---"
check_cmd aria2c
check_cmd rclone
check_cmd python3

echo "--- Python ---"
python3 --version 2>/dev/null || echo "  python3 not available"

echo "--- Done ---"
