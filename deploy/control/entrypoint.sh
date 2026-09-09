#!/usr/bin/env bash
set -euo pipefail
mkdir -p /run/rtgs
printf '%s\n' "${RTGS_OPERATOR_TOKEN:?Set the team dashboard password}" | htpasswd -iBc /run/rtgs/htpasswd "${RTGS_OPERATOR_USER:-rtgs}" >/dev/null
chown root:www-data /run/rtgs/htpasswd
chmod 640 /run/rtgs/htpasswd
pids=()
finish() {
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap finish EXIT INT TERM
python /opt/rtgs/backend/control_server.py &
pids+=("$!")
node /opt/rtgs/frontend/server.js &
pids+=("$!")
nginx -c /opt/rtgs/deploy/control/nginx.conf -g 'daemon off;' &
pids+=("$!")
wait -n "${pids[@]}"
