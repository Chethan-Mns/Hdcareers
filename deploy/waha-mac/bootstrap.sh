#!/bin/bash
# Safe local-only credential init; never display credentials.
set -euo pipefail
umask 077
if [[ "$(uname -s)" != Darwin ]]; then echo "This bootstrap requires macOS." >&2; exit 2; fi
if [[ -e .env || -e .waha-api-key.secret ]]; then echo "Existing credentials detected; refusing overwrite." >&2; exit 1; fi
for tool in openssl shasum; do command -v "$tool" >/dev/null || { echo "Missing $tool"; exit 1; }; done
api_key="$(openssl rand -hex 32)"
dashboard_password="$(openssl rand -hex 32)"
hash="$(printf %s "$api_key" | shasum -a 512 | awk '{print $1}')"
printf '%s\n' "$api_key" > .waha-api-key.secret
cat > .env <<ENV
WAHA_API_KEY=sha512:$hash
WAHA_DASHBOARD_USERNAME=hd_admin
WAHA_DASHBOARD_PASSWORD=$dashboard_password
ENV
chmod 600 .env .waha-api-key.secret
mkdir -p .sessions
chmod 700 .sessions
echo "Generated private credentials. Password in .env, GitHub API key in .waha-api-key.secret."
echo "Next: docker compose up -d"
