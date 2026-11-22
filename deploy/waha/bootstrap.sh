#!/usr/bin/env bash
set -euo pipefail
umask 077
domain="${1:-}"
if [[ ! "$domain" =~ ^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$ ]]; then
  echo "Usage: bash bootstrap.sh waha.yourdomain.example" >&2
  exit 2
fi
if [[ -e .env || -e .waha-api-key.secret ]]; then
  echo "Existing credentials detected. Refusing to overwrite them." >&2
  exit 1
fi
if ! command -v openssl >/dev/null 2>&1; then
  echo "Install openssl first." >&2
  exit 1
fi
api_key="$(openssl rand -hex 32)"
dashboard_password="$(openssl rand -hex 32)"
api_hash="$(printf %s "$api_key" | sha512sum | awk '{print $1}')"
printf '%s\n' "$api_key" > .waha-api-key.secret
cat > .env <<ENV
WAHA_DOMAIN=$domain
WAHA_API_KEY=sha512:$api_hash
WAHA_DASHBOARD_USERNAME=hd_admin
WAHA_DASHBOARD_PASSWORD=$dashboard_password
WAHA_PRINT_QR=false
ENV
chmod 600 .env .waha-api-key.secret
mkdir -p .sessions
chmod 700 .sessions
echo "Local credentials generated; never commit .env or .waha-api-key.secret."
echo "Set the DNS A record, allow TLS ports 80/443, then run docker compose up -d."
