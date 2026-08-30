#!/usr/bin/env bash
set -euo pipefail

ROOT=/opt/rtgs
mkdir -p /run/rtgs "${RTGS_DATA_DIR:-/workspace/rtgs-data}"

operator_user="${RTGS_OPERATOR_USER:-rtgs}"
operator_token="${RTGS_OPERATOR_TOKEN:?RTGS_OPERATOR_TOKEN is required}"
htpasswd -bc /run/rtgs/htpasswd "$operator_user" "$operator_token" >/dev/null

export RTGS_DATA_DIR="${RTGS_DATA_DIR:-/workspace/rtgs-data}"
export RTGS_ARTIFACT_POLICY="${RTGS_ARTIFACT_POLICY:-compact}"
export RTGS_MODE="${RTGS_MODE:-live}"
export PYTHONPATH="$ROOT/backend"
export PORT=3000
export HOSTNAME=127.0.0.1
export NODE_ENV=production
export NEXT_PUBLIC_DEMO_MODE=false

pids=()
finish() {
  local pid
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap finish EXIT INT TERM

nginx -c "$ROOT/deploy/gateway/nginx.conf" -g 'daemon off;' &
pids+=("$!")
node "$ROOT/frontend/server.js" &
pids+=("$!")

if [[ "$RTGS_MODE" != live ]]; then
  python "$ROOT/backend/postgame_server.py" &
  pids+=("$!")
fi

if [[ "$RTGS_MODE" == replay ]]; then
  python "$ROOT/backend/replay_server.py" --scenario "${RTGS_REPLAY_SCENARIO:-standard}" --port 8001 &
else
  relay_read_url="${RTGS_RELAY_READ_URL:?RTGS_RELAY_READ_URL is required for live CV}"
  export HEADLESS=1
  export RTGS_OBSERVATION_RECORDING="$RTGS_DATA_DIR/live-observations.jsonl.gz"
  python "$ROOT/backend/soccer_analytics.py" --stream "$relay_read_url" --headless --port 8001 &
fi
pids+=("$!")

wait -n "${pids[@]}"
