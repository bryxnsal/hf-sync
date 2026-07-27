#!/usr/bin/env bash
# Start aria2 RPC daemon
set -euo pipefail

ARIA2_CONF="${ARIA2_CONF:-aria2.conf}"

aria2c --enable-rpc --rpc-listen-all --rpc-allow-origin-all \
  --conf-path="$ARIA2_CONF" \
  --daemon=true
