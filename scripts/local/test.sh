#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
setup_dev_python
setup_frontend

export PYTHONPATH="$RTGS_ROOT/backend"
"$RTGS_DEV_VENV/bin/python" -m pytest -q "$RTGS_ROOT/backend/tests"
"$RTGS_DEV_VENV/bin/python" -m py_compile "$RTGS_ROOT/scripts/cloud.py" "$RTGS_ROOT/backend/replay_server.py"
(cd "$RTGS_ROOT/frontend" && npm test)
(cd "$RTGS_ROOT/frontend" && RTGS_MODE=test NEXT_PUBLIC_DEMO_MODE=false npm run build)
bash -n "$RTGS_ROOT/rtgs" "$RTGS_ROOT"/scripts/local/*.sh "$RTGS_ROOT"/scripts/runpod/*.sh \
  "$RTGS_ROOT"/scripts/relay/*.sh "$RTGS_ROOT"/deploy/runpod/*.sh
