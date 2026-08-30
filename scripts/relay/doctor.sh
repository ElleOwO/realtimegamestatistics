#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-}"
[[ -n "$DOMAIN" ]] || { echo "Usage: ./rtgs relay doctor relay.example.com" >&2; exit 2; }
PUBLISH_USER="${RTGS_RELAY_PUBLISH_USER:-publisher}"
PUBLISH_PASSWORD="${RTGS_RELAY_PUBLISH_PASSWORD:-}"
READ_USER="${RTGS_RELAY_READ_USER:-reader}"
READ_PASSWORD="${RTGS_RELAY_READ_PASSWORD:-}"
[[ -n "$PUBLISH_PASSWORD" && -n "$READ_PASSWORD" ]] || {
  echo "Set RTGS_RELAY_PUBLISH_PASSWORD and RTGS_RELAY_READ_PASSWORD." >&2
  exit 2
}

publish_url="rtmps://$DOMAIN:1936/live?user=$PUBLISH_USER&pass=$PUBLISH_PASSWORD"
read_url="rtmps://$DOMAIN:1936/live?user=$READ_USER&pass=$READ_PASSWORD"
ffmpeg -hide_banner -loglevel error -re -f lavfi -i testsrc=size=640x360:rate=10 \
  -t 8 -c:v libx264 -preset ultrafast -tune zerolatency -g 10 -pix_fmt yuv420p \
  -f flv "$publish_url" &
publisher_pid=$!
trap 'kill "$publisher_pid" 2>/dev/null || true' EXIT
sleep 2
ffprobe -v error -read_intervals %+2 -select_streams v:0 -show_entries stream=codec_name,width,height -of json "$read_url"
wait "$publisher_pid"
echo "Relay publish/read/TLS check passed."
