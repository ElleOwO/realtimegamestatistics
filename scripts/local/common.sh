#!/usr/bin/env bash
set -euo pipefail

RTGS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RTGS_LOCAL_DIR="$RTGS_ROOT/.rtgs/local"
RTGS_DEV_VENV="$RTGS_LOCAL_DIR/venv"

setup_dev_python() {
  mkdir -p "$RTGS_LOCAL_DIR"
  if [[ ! -x "$RTGS_DEV_VENV/bin/python" ]]; then
    python3 -m venv "$RTGS_DEV_VENV"
  fi
  local fingerprint stamp
  fingerprint="$(sha256sum "$RTGS_ROOT/backend/requirements-dev.txt" | awk '{print $1}')"
  stamp="$RTGS_DEV_VENV/.requirements.sha256"
  if [[ ! -f "$stamp" || "$(<"$stamp")" != "$fingerprint" ]]; then
    "$RTGS_DEV_VENV/bin/python" -m pip install --upgrade pip || return 1
    "$RTGS_DEV_VENV/bin/python" -m pip install -r "$RTGS_ROOT/backend/requirements-dev.txt" || return 1
    printf '%s\n' "$fingerprint" > "$stamp"
  fi
}

setup_frontend() {
  if [[ ! -x "$RTGS_ROOT/frontend/node_modules/.bin/next" ]]; then
    (cd "$RTGS_ROOT/frontend" && npm install --legacy-peer-deps)
  fi
}
