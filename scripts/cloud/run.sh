#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../local" && pwd)/common.sh"
setup_dev_python
exec "$RTGS_DEV_VENV/bin/python" "$RTGS_ROOT/scripts/cloud.py" "$@"
