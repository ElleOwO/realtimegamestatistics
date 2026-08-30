#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

KEEP_DATA=0
SCENARIO=standard
REPLAY_SPEED=0.1
while (($#)); do
  case "$1" in
    --keep-data) KEEP_DATA=1 ;;
    --scenario) shift; SCENARIO="${1:?--scenario needs a name}" ;;
    --speed) shift; REPLAY_SPEED="${1:?--speed needs a multiplier}" ;;
    -h|--help)
      echo "Usage: ./rtgs dev [--scenario standard] [--speed 0.1] [--keep-data]"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

setup_dev_python
setup_frontend

RUN_DATA="$(mktemp -d /tmp/rtgs-dev.XXXXXX)"
PIDS=()
cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  if ((KEEP_DATA)); then
    echo "Replay data kept at $RUN_DATA"
  else
    rm -rf "$RUN_DATA"
  fi
}
trap cleanup EXIT INT TERM

export RTGS_DATA_DIR="$RUN_DATA"
export RTGS_DATABASE_URL="sqlite:///$RUN_DATA/rtgs.sqlite3"
export RTGS_MODE=replay
export RTGS_ARTIFACT_POLICY=compact
export RTGS_REPLAY_SCENARIO="$SCENARIO"
export NEXT_PUBLIC_API_URL=http://localhost:8000
export NEXT_PUBLIC_WS_URL=ws://localhost:8001/ws
export NEXT_PUBLIC_DEMO_MODE=false
export PYTHONPATH="$RTGS_ROOT/backend"

"$RTGS_DEV_VENV/bin/python" "$RTGS_ROOT/backend/postgame_server.py" &
PIDS+=("$!")
"$RTGS_DEV_VENV/bin/python" "$RTGS_ROOT/backend/replay_server.py" --scenario "$SCENARIO" --speed "$REPLAY_SPEED" --port 8001 &
PIDS+=("$!")
(cd "$RTGS_ROOT/frontend" && npm run dev) &
PIDS+=("$!")

for _attempt in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 \
    && curl -fsS http://127.0.0.1:8001/health >/dev/null 2>&1 \
    && curl -fsS http://127.0.0.1:3000/ >/dev/null 2>&1; then
    echo
    echo "RTGS replay is ready:"
    echo "  Live:      http://localhost:3000/"
    echo "  Post-game: http://localhost:3000/matches"
    echo "Start the first half from the live operator bar. Ctrl+C stops and cleans the run."
    wait
    exit 0
  fi
  sleep 1
done

echo "RTGS replay did not become healthy within 60 seconds." >&2
exit 1
