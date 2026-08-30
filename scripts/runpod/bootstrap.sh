#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
RUNTIME_DIR="$ROOT_DIR/.rtgs"
ORT_DIR="$RUNTIME_DIR/onnxruntime-gpu"
LOCAL_RUNTIME_DIR="${RTGS_LOCAL_RUNTIME_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/rtgs}"
FRONTEND_RUNTIME_DIR="$LOCAL_RUNTIME_DIR/frontend"
NODE_VERSION="${RTGS_NODE_VERSION:-20.19.4}"
INSTALL_FRONTEND=1
START_SERVICES=1

usage() {
  cat <<'EOF'
Usage: ./rtgs bootstrap [--skip-frontend] [--no-start]

Prepare an RTGS RunPod from a PyTorch/CUDA template. The operation is
idempotent. Match data stays under the repository; disposable dashboard build
files use the pod's faster local container disk.

Options:
  --skip-frontend  Install and validate only the post-game API/GPU worker.
  --no-start       Prepare the environment without starting services.
EOF
}

while (($#)); do
  case "$1" in
    --skip-frontend) INSTALL_FRONTEND=0 ;;
    --no-start) START_SERVICES=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

step() {
  printf '\n\033[1;36m==> %s\033[0m\n' "$1"
}

fail() {
  printf '\nERROR: %s\n' "$1" >&2
  exit 1
}

if command -v tmux >/dev/null 2>&1 && tmux has-session -t rtgs-api 2>/dev/null; then
  fail "RTGS is running. Use './rtgs stop' before changing its environment."
fi

step "Checking the RunPod base image"
if [[ "$ROOT_DIR" != /workspace/* ]]; then
  echo "Warning: clone the repository under /workspace so code, models, and match data survive pod stops."
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || fail "python3 is missing; use a RunPod PyTorch template with Python 3.11."
"$PYTHON_BIN" - <<'PY' || exit 1
import sys
if not ((3, 10) <= sys.version_info[:2] < (3, 13)):
    raise SystemExit(f"Python {sys.version.split()[0]} is unsupported; use Python 3.11 or 3.12.")
print("Python:", sys.version.split()[0])
PY

command -v nvidia-smi >/dev/null 2>&1 || fail "No NVIDIA runtime was found; attach a GPU to this pod."
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -n 1
"$PYTHON_BIN" - <<'PY' || fail "The base image cannot access CUDA through PyTorch. Use a RunPod PyTorch/CUDA template."
import torch
if not torch.cuda.is_available():
    raise SystemExit(1)
print("Base PyTorch:", torch.__version__)
print("CUDA device:", torch.cuda.get_device_name(0))
PY

step "Installing operating-system dependencies"
packages=(ca-certificates curl ffmpeg git libgl1 libglib2.0-0 rsync tmux xz-utils)
missing_packages=()
if command -v dpkg-query >/dev/null 2>&1; then
  for package_name in "${packages[@]}"; do
    dpkg-query -W -f='${Status}' "$package_name" 2>/dev/null | grep -q 'ok installed' || missing_packages+=("$package_name")
  done
else
  for command_name in curl ffmpeg git rsync tmux xz; do
    command -v "$command_name" >/dev/null 2>&1 || missing_packages+=("$command_name")
  done
fi
if ((${#missing_packages[@]})); then
  command -v apt-get >/dev/null 2>&1 || fail "Missing ${missing_packages[*]} and apt-get is unavailable."
  if [[ "$(id -u)" -eq 0 ]]; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${packages[@]}"
  elif command -v sudo >/dev/null 2>&1; then
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${packages[@]}"
  else
    fail "Root or sudo access is required to install ${missing_packages[*]}."
  fi
else
  echo "System tools already present."
fi

step "Creating the Python environment"
mkdir -p "$RUNTIME_DIR"
venv_created=0
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv --system-site-packages "$VENV_DIR"
  venv_created=1
fi
python_stamp="$RUNTIME_DIR/python-environment.sha256"
python_fingerprint="$({
  sha256sum "$ROOT_DIR/backend/constraints-runpod.txt" "$ROOT_DIR/backend/requirements-runpod.txt"
  printf '%s\n' 'onnxruntime-gpu==1.22.0'
  "$VENV_DIR/bin/python" --version
} | sha256sum | awk '{print $1}')"
if [[ "$venv_created" -eq 0 && -f "$python_stamp" && "$(<"$python_stamp")" == "$python_fingerprint" ]]; then
  echo "Python and CUDA dependencies are already current."
else
  "$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools "wheel==0.45.1"
  "$VENV_DIR/bin/python" -m pip install \
    --constraint "$ROOT_DIR/backend/constraints-runpod.txt" \
    --requirement "$ROOT_DIR/backend/requirements-runpod.txt"

  step "Installing CUDA ONNX Runtime"
  mkdir -p "$ORT_DIR"
  "$VENV_DIR/bin/python" -m pip install \
    --upgrade --target "$ORT_DIR" --no-deps onnxruntime-gpu==1.22.0
  printf '%s\n' "$python_fingerprint" > "$python_stamp"
fi

step "Creating persistent runtime configuration"
mkdir -p "$RUNTIME_DIR" "$ROOT_DIR/data/inbox" "$ROOT_DIR/data/matches"
if [[ ! -s "$ROOT_DIR/.env" ]]; then
  if [[ -z "${ROBOFLOW_API_KEY:-}" ]]; then
    [[ -t 0 ]] || fail "ROBOFLOW_API_KEY is missing. Export it before running a non-interactive bootstrap."
    read -rsp "Roboflow API key: " ROBOFLOW_API_KEY
    echo
  fi
  [[ -n "${ROBOFLOW_API_KEY:-}" ]] || fail "The Roboflow API key cannot be empty."
  umask 077
  {
    printf 'ROBOFLOW_API_KEY=%s\n' "$ROBOFLOW_API_KEY"
    printf 'RTGS_DATA_DIR=%s\n' "$ROOT_DIR/data"
    printf 'ANALYSIS_HZ=%s\n' "${ANALYSIS_HZ:-10}"
    printf 'KEYPOINT_HZ=%s\n' "${KEYPOINT_HZ:-2}"
    printf 'PROGRESS_HZ=%s\n' "${PROGRESS_HZ:-2}"
    printf 'RTGS_CORS_ORIGINS=%s\n' "${RTGS_CORS_ORIGINS:-*}"
  } > "$ROOT_DIR/.env"
  echo "Created the gitignored .env file."
else
  echo "Keeping the existing .env file."
fi

if ((INSTALL_FRONTEND)); then
  step "Installing Node.js ${NODE_VERSION} and building the dashboard"
  mkdir -p "$LOCAL_RUNTIME_DIR" "$FRONTEND_RUNTIME_DIR"
  machine="$(uname -m)"
  case "$machine" in
    x86_64|amd64) node_arch="x64" ;;
    aarch64|arm64) node_arch="arm64" ;;
    *) fail "Unsupported Node.js architecture: $machine" ;;
  esac
  node_name="node-v${NODE_VERSION}-linux-${node_arch}"
  node_home="$LOCAL_RUNTIME_DIR/$node_name"
  node_marker="$node_home/.rtgs-install-complete"
  if [[ ! -f "$node_marker" ]]; then
    temp_dir="$(mktemp -d)"
    archive="$node_name.tar.xz"
    curl -fsSLo "$temp_dir/$archive" "https://nodejs.org/dist/v${NODE_VERSION}/$archive"
    curl -fsSLo "$temp_dir/SHASUMS256.txt" "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt"
    (
      cd "$temp_dir"
      grep "  $archive\$" SHASUMS256.txt | sha256sum --check --strict
    )
    mkdir -p "$node_home"
    tar --no-same-owner --strip-components=1 -xJf "$temp_dir/$archive" -C "$node_home"
    touch "$node_marker"
    rm -rf "$temp_dir"
  fi
  ln -sfn "$node_home" "$LOCAL_RUNTIME_DIR/node"
  export PATH="$LOCAL_RUNTIME_DIR/node/bin:$PATH"

  if [[ -n "${NEXT_PUBLIC_API_URL:-}" ]]; then
    public_api_url="$NEXT_PUBLIC_API_URL"
  elif [[ -n "${RUNPOD_POD_ID:-}" ]]; then
    public_api_url="https://${RUNPOD_POD_ID}-8000.proxy.runpod.net"
  else
    public_api_url="http://localhost:8000"
  fi
  if [[ -n "${NEXT_PUBLIC_WS_URL:-}" ]]; then
    public_ws_url="$NEXT_PUBLIC_WS_URL"
  elif [[ -n "${RUNPOD_POD_ID:-}" ]]; then
    public_ws_url="wss://${RUNPOD_POD_ID}-8001.proxy.runpod.net/ws"
  else
    public_ws_url="ws://localhost:8001/ws"
  fi

  # npm performs thousands of small writes. RunPod's /workspace network volume
  # is ideal for durable match data but can fail or become extremely slow for
  # node_modules, so stage the dashboard on the container's local disk.
  rsync -a --delete \
    --exclude '.next/' \
    --exclude 'node_modules/' \
    "$ROOT_DIR/frontend/" "$FRONTEND_RUNTIME_DIR/"

  dependency_fingerprint="$({
    sha256sum "$FRONTEND_RUNTIME_DIR/package.json"
    [[ ! -f "$FRONTEND_RUNTIME_DIR/package-lock.json" ]] || \
      sha256sum "$FRONTEND_RUNTIME_DIR/package-lock.json"
  } | sha256sum | awk '{print $1}')"
  dependency_stamp="$LOCAL_RUNTIME_DIR/frontend-dependencies.sha256"
  if [[ -x "$FRONTEND_RUNTIME_DIR/node_modules/.bin/next" && \
        -f "$dependency_stamp" && \
        "$(<"$dependency_stamp")" == "$dependency_fingerprint" ]]; then
    echo "Dashboard dependencies are already current."
  else
    (
      cd "$FRONTEND_RUNTIME_DIR"
      if [[ -f package-lock.json ]]; then
        npm ci --legacy-peer-deps --no-audit --no-fund --loglevel=warn
      else
        npm install --legacy-peer-deps --no-audit --no-fund --loglevel=warn
      fi
    )
    printf '%s\n' "$dependency_fingerprint" > "$dependency_stamp"
  fi

  (
    cd "$FRONTEND_RUNTIME_DIR"
    NEXT_PUBLIC_API_URL="$public_api_url" \
      NEXT_PUBLIC_WS_URL="$public_ws_url" \
      NEXT_PUBLIC_DEMO_MODE=false \
      npm run build
  )
  mkdir -p "$FRONTEND_RUNTIME_DIR/.next/standalone/.next"
  rsync -a --delete \
    "$FRONTEND_RUNTIME_DIR/public/" \
    "$FRONTEND_RUNTIME_DIR/.next/standalone/public/"
  rsync -a --delete \
    "$FRONTEND_RUNTIME_DIR/.next/static/" \
    "$FRONTEND_RUNTIME_DIR/.next/standalone/.next/static/"
  {
    printf 'RTGS_NODE_HOME=%q\n' "$LOCAL_RUNTIME_DIR/node"
    printf 'RTGS_FRONTEND_DIR=%q\n' "$FRONTEND_RUNTIME_DIR"
    printf 'NEXT_PUBLIC_API_URL=%q\n' "$public_api_url"
    printf 'NEXT_PUBLIC_WS_URL=%q\n' "$public_ws_url"
  } > "$RUNTIME_DIR/frontend.env"
fi

step "Validating the installed runtime"
RTGS_ROOT="$ROOT_DIR" bash "$ROOT_DIR/scripts/runpod/service.sh" doctor
PYTHONPATH="$ORT_DIR:$ROOT_DIR/backend" "$VENV_DIR/bin/pytest" -q "$ROOT_DIR/backend/tests"

if ((START_SERVICES)); then
  step "Starting RTGS"
  bash "$ROOT_DIR/scripts/runpod/service.sh" start
else
  echo
  echo "Environment ready. Start it later with: ./rtgs start"
fi
