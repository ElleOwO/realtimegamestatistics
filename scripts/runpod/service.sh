#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${RTGS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
VENV_DIR="$ROOT_DIR/.venv"
RUNTIME_DIR="$ROOT_DIR/.rtgs"
ORT_DIR="${RTGS_ORT_DIR:-$RUNTIME_DIR/onnxruntime-gpu}"
LOCAL_RUNTIME_DIR="${RTGS_LOCAL_RUNTIME_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/rtgs}"
SCRIPT_PATH="$ROOT_DIR/scripts/runpod/service.sh"
API_SESSION="rtgs-api"
UI_SESSION="rtgs-ui"

load_runtime() {
  [[ -x "$VENV_DIR/bin/python" ]] || {
    echo "RTGS is not bootstrapped. Run './rtgs bootstrap' first." >&2
    exit 1
  }
  if [[ -s "$ROOT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.env"
    set +a
  fi
  if [[ -s "$RUNTIME_DIR/frontend.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$RUNTIME_DIR/frontend.env"
    set +a
  fi
  export RTGS_DATA_DIR="${RTGS_DATA_DIR:-$ROOT_DIR/data}"
  export RTGS_NODE_HOME="${RTGS_NODE_HOME:-$LOCAL_RUNTIME_DIR/node}"
  export RTGS_FRONTEND_DIR="${RTGS_FRONTEND_DIR:-$LOCAL_RUNTIME_DIR/frontend}"
  export PYTHONPATH="$ORT_DIR:$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"
  export PATH="$RTGS_NODE_HOME/bin:$PATH"
  mkdir -p "$RTGS_DATA_DIR/inbox" "$RTGS_DATA_DIR/matches"
}

has_session() {
  tmux has-session -t "$1" 2>/dev/null
}

wait_for_api() {
  local attempt
  for attempt in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_services() {
  load_runtime
  command -v tmux >/dev/null 2>&1 || {
    echo "tmux is missing. Re-run './rtgs bootstrap'." >&2
    exit 1
  }
  [[ -s "$ROOT_DIR/.env" ]] || {
    echo "The persistent .env file is missing. Re-run './rtgs bootstrap'." >&2
    exit 1
  }
  if [[ -s "$RUNTIME_DIR/frontend.env" && \
        ( ! -x "$RTGS_NODE_HOME/bin/node" || \
          ! -f "$RTGS_FRONTEND_DIR/.next/standalone/server.js" ) ]]; then
    echo "The disposable dashboard cache is missing (normally after a pod restart)."
    echo "Rebuilding it automatically with './rtgs bootstrap'."
    exec bash "$ROOT_DIR/scripts/runpod/bootstrap.sh"
  fi

  if has_session "$API_SESSION"; then
    echo "Post-game API is already running."
  else
    tmux new-session -d -s "$API_SESSION" -c "$ROOT_DIR" \
      -e "RTGS_ROOT=$ROOT_DIR" -e "RTGS_ORT_DIR=$ORT_DIR" \
      "$SCRIPT_PATH _serve-api"
    echo "Started post-game API and GPU worker."
  fi
  if ! wait_for_api; then
    echo "The API did not become healthy. Inspect it with './rtgs logs api'." >&2
    exit 1
  fi

  if [[ -x "$RTGS_NODE_HOME/bin/node" && \
        -f "$RTGS_FRONTEND_DIR/.next/standalone/server.js" ]]; then
    if has_session "$UI_SESSION"; then
      echo "Dashboard is already running."
    else
      tmux new-session -d -s "$UI_SESSION" -c "$ROOT_DIR" \
        -e "RTGS_ROOT=$ROOT_DIR" -e "RTGS_ORT_DIR=$ORT_DIR" \
        "$SCRIPT_PATH _serve-ui"
      echo "Started dashboard."
    fi
  else
    echo "Dashboard was not built; run './rtgs bootstrap' without --skip-frontend."
  fi
  print_urls
}

stop_one() {
  local session="$1"
  if ! has_session "$session"; then
    return
  fi
  tmux send-keys -t "$session" C-c
  sleep 1
  has_session "$session" && tmux kill-session -t "$session" || true
}

stop_services() {
  stop_one "$UI_SESSION"
  stop_one "$API_SESSION"
  echo "RTGS services stopped. Match data remains under data/."
}

session_status() {
  local label="$1" session="$2" url="$3"
  if has_session "$session"; then
    if [[ -n "$url" ]] && curl -fsS "$url" >/dev/null 2>&1; then
      printf '%-12s running and healthy\n' "$label"
    else
      printf '%-12s running (health response pending)\n' "$label"
    fi
  else
    printf '%-12s stopped\n' "$label"
  fi
}

status_services() {
  session_status "API" "$API_SESSION" "http://127.0.0.1:8000/health"
  session_status "Dashboard" "$UI_SESSION" "http://127.0.0.1:3000/matches"
  if curl -fsS http://127.0.0.1:8000/api/v1/matches >/dev/null 2>&1; then
    "$VENV_DIR/bin/python" - <<'PY'
import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/matches") as response:
    matches = json.load(response)
active = [m for m in matches if (m.get("latest_job") or {}).get("state") in {"queued", "preflight", "running"}]
for match in active:
    job = match["latest_job"]
    print(f"Active job   {match['id']}  {job['state']}  {job['progress'] * 100:.1f}%")
PY
  fi
}

print_urls() {
  echo
  if [[ -n "${RUNPOD_POD_ID:-}" ]]; then
    echo "Dashboard: https://${RUNPOD_POD_ID}-8000.proxy.runpod.net/matches"
    echo "API:       https://${RUNPOD_POD_ID}-8000.proxy.runpod.net/api/v1"
  else
    echo "Dashboard: http://localhost:8000/matches"
    echo "API:       http://localhost:8000/api/v1"
  fi
}

show_logs() {
  local target="${1:-api}" session
  case "$target" in
    api) session="$API_SESSION" ;;
    ui|frontend) session="$UI_SESSION" ;;
    *) echo "Use './rtgs logs api' or './rtgs logs ui'." >&2; exit 2 ;;
  esac
  has_session "$session" || {
    echo "$target is not running." >&2
    exit 1
  }
  tmux capture-pane -pt "$session" -S -200
}

doctor() {
  load_runtime
  command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg: missing"; exit 1; }
  command -v tmux >/dev/null 2>&1 || { echo "tmux: missing"; exit 1; }
  "$VENV_DIR/bin/python" - <<'PY'
import cv2
import fastapi
import inference
import onnxruntime
import supervision
import torch
import uvicorn
from inference import get_model
from importlib.metadata import version

if not torch.cuda.is_available():
    raise SystemExit("CUDA: unavailable")
providers = onnxruntime.get_available_providers()
if "CUDAExecutionProvider" not in providers:
    raise SystemExit(f"ONNX Runtime CUDA provider missing: {providers}")
print("Python imports: ok")
print("PyTorch:", torch.__version__)
print("GPU:", torch.cuda.get_device_name(0))
print("OpenCV:", cv2.__version__)
print("ONNX providers:", ", ".join(providers))
print("FastAPI:", fastapi.__version__)
print("Inference:", version("inference"))
print("Roboflow model loader: ok")
print("Uvicorn:", uvicorn.__version__)
print("Supervision:", supervision.__version__)
PY
  if [[ -s "$ROOT_DIR/.env" ]] && grep -q '^ROBOFLOW_API_KEY=.' "$ROOT_DIR/.env"; then
    echo "Roboflow key: configured"
  elif [[ -n "${ROBOFLOW_API_KEY:-}" ]]; then
    echo "Roboflow key: configured in environment"
  else
    echo "Roboflow key: missing"
    exit 1
  fi
  echo "FFmpeg: $(ffmpeg -version | head -n 1)"
}

serve_api() {
  load_runtime
  exec "$VENV_DIR/bin/python" "$ROOT_DIR/backend/postgame_server.py"
}

serve_ui() {
  load_runtime
  export NODE_ENV=production
  export PORT="${PORT:-3000}"
  export HOSTNAME="${RTGS_UI_HOST:-0.0.0.0}"
  exec "$RTGS_NODE_HOME/bin/node" "$RTGS_FRONTEND_DIR/.next/standalone/server.js"
}

usage() {
  cat <<'EOF'
Usage: ./rtgs COMMAND

Commands:
  bootstrap       Install and configure a RunPod (handled by bootstrap.sh)
  start           Start the post-game API/GPU worker and dashboard
  stop            Stop both services without deleting match data
  restart         Restart both services
  status          Show service health and any active analysis job
  logs [api|ui]   Show recent service logs
  attach [api|ui] Attach interactively to a service (Ctrl-b d to detach)
  doctor          Verify Python, CUDA, ONNX Runtime, FFmpeg, and configuration
  urls            Print local or RunPod dashboard/API URLs
EOF
}

case "${1:-help}" in
  start) start_services ;;
  stop) stop_services ;;
  restart) stop_services; start_services ;;
  status) load_runtime; status_services ;;
  logs) show_logs "${2:-api}" ;;
  attach)
    case "${2:-api}" in api) session="$API_SESSION" ;; ui|frontend) session="$UI_SESSION" ;; *) exit 2 ;; esac
    exec tmux attach-session -t "$session"
    ;;
  doctor) doctor ;;
  urls) print_urls ;;
  _serve-api) serve_api ;;
  _serve-ui) serve_ui ;;
  help|-h|--help) usage ;;
  *) echo "Unknown command: $1" >&2; usage >&2; exit 2 ;;
esac
