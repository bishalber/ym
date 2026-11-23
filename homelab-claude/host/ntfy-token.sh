#!/usr/bin/env bash
# Run ON THE HOST after creating your ntfy user:
#   docker exec -it claude-ntfy ntfy user add --role=admin <name>      (asks for a password)
#   bash host/ntfy-token.sh <name>
# Creates an access token for the runner, stores it in .env (never printed), recreates claude-box
# so it picks it up, and sends a test notification.
set -euo pipefail
cd "${STACK_DIR:-/opt/homelab-claude}"
U="${1:?usage: ntfy-token.sh <ntfy-username>}"
T="$(docker exec claude-ntfy ntfy token add --label claude-runner "$U" 2>&1 | grep -oE 'tk_[a-z0-9]+' | head -1 || true)"
[ -n "$T" ] || { echo "could not create a token: does ntfy user '$U' exist? (docker exec claude-ntfy ntfy user list)"; exit 1; }
sed -i '/^NTFY_RUNNER_TOKEN=/d' .env && printf 'NTFY_RUNNER_TOKEN=%s\n' "$T" >> .env
docker compose up -d claude-box 2>&1 | tail -1
C=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $T" -H "Title: homelab test" -d "ntfy works: job and backup alerts will arrive here" http://127.0.0.1:2586/claude-jobs)
echo "test notification: HTTP $C (200 = sent; open the ntfy app to see it)"
unset T
