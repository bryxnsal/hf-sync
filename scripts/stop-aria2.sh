#!/usr/bin/env bash
# Stop aria2 RPC daemon
set -euo pipefail

pkill aria2c 2>/dev/null || echo "aria2c not running"
