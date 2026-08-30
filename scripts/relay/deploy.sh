#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${1:-}"
DOMAIN="${2:-}"
if [[ -z "$TARGET" || -z "$DOMAIN" ]]; then
  echo "Usage: ./rtgs relay deploy USER@HOST relay.example.com" >&2
  exit 2
fi

PUBLISH_USER="${RTGS_RELAY_PUBLISH_USER:-publisher}"
PUBLISH_PASSWORD="${RTGS_RELAY_PUBLISH_PASSWORD:-}"
READ_USER="${RTGS_RELAY_READ_USER:-reader}"
READ_PASSWORD="${RTGS_RELAY_READ_PASSWORD:-}"
CERTBOT_EMAIL="${RTGS_RELAY_CERTBOT_EMAIL:-}"

for value in "$DOMAIN" "$PUBLISH_USER" "$PUBLISH_PASSWORD" "$READ_USER" "$READ_PASSWORD"; do
  [[ "$value" =~ ^[A-Za-z0-9._-]+$ ]] || {
    echo "Relay domain, users, and passwords may contain only letters, numbers, dot, underscore, and dash." >&2
    exit 2
  }
done
[[ -n "$PUBLISH_PASSWORD" && -n "$READ_PASSWORD" && -n "$CERTBOT_EMAIL" ]] || {
  echo "Set RTGS_RELAY_PUBLISH_PASSWORD, RTGS_RELAY_READ_PASSWORD, and RTGS_RELAY_CERTBOT_EMAIL." >&2
  exit 2
}
[[ "$TARGET" =~ ^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$ ]] || {
  echo "Relay target must be USER@HOST using letters, numbers, dot, underscore, or dash." >&2
  exit 2
}
[[ "$CERTBOT_EMAIL" =~ ^[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+$ ]] || {
  echo "RTGS_RELAY_CERTBOT_EMAIL contains unsupported characters." >&2
  exit 2
}

TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT
cp "$ROOT_DIR/deploy/relay/compose.yml" "$TEMP_DIR/compose.yml"
sed \
  -e "s/__RELAY_DOMAIN__/$DOMAIN/g" \
  -e "s/__PUBLISH_USER__/$PUBLISH_USER/g" \
  -e "s/__PUBLISH_PASSWORD__/$PUBLISH_PASSWORD/g" \
  -e "s/__READ_USER__/$READ_USER/g" \
  -e "s/__READ_PASSWORD__/$READ_PASSWORD/g" \
  "$ROOT_DIR/deploy/relay/mediamtx.yml" > "$TEMP_DIR/mediamtx.yml"

ssh "$TARGET" "if ! command -v docker >/dev/null || ! command -v certbot >/dev/null; then sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2 certbot; fi; sudo mkdir -p /opt/rtgs-relay && sudo chown \$(id -u):\$(id -g) /opt/rtgs-relay"
scp "$TEMP_DIR/compose.yml" "$TEMP_DIR/mediamtx.yml" "$TARGET:/opt/rtgs-relay/"
ssh "$TARGET" "sudo chmod 600 /opt/rtgs-relay/mediamtx.yml && sudo certbot certonly --standalone --non-interactive --agree-tos --email '$CERTBOT_EMAIL' -d '$DOMAIN' && cd /opt/rtgs-relay && sudo docker compose -f compose.yml up -d"
ssh "$TARGET" "sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy && printf '%s\n' '#!/bin/sh' 'cd /opt/rtgs-relay && docker compose -f compose.yml restart mediamtx' | sudo tee /etc/letsencrypt/renewal-hooks/deploy/restart-rtgs-relay.sh >/dev/null && sudo chmod 755 /etc/letsencrypt/renewal-hooks/deploy/restart-rtgs-relay.sh"

echo "Relay deployed. Configure the phone with:"
echo "  rtmps://$DOMAIN:1936/live?user=$PUBLISH_USER&pass=YOUR_PASSWORD"
echo "RunPod reads:"
echo "  rtmps://$DOMAIN:1936/live?user=$READ_USER&pass=YOUR_PASSWORD"
