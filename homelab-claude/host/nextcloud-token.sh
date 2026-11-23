#!/usr/bin/env bash
# Run ON THE HOST. Creates a Nextcloud app password named claude-ro for NEXTCLOUD_USER (from .env)
# without needing the login password (works with the default master-key encryption), tests it,
# saves it to .env, restarts nextcloud-ro and lists your files. The token is never printed.
set -u
cd "${STACK_DIR:-/opt/homelab-claude}" || exit 1
NCU="$(grep -m1 '^NEXTCLOUD_USER=' .env | cut -d= -f2-)"; [ -n "$NCU" ] || { echo "set NEXTCLOUD_USER in .env first"; exit 1; }
O="$(docker exec -u www-data nextcloud-app-1 php occ user:auth-tokens:add -n --name claude-ro "$NCU" </dev/null 2>&1)"
T="$(printf '%s\n' "$O" | tail -n 1 | tr -d '[:space:]')"
C=$(curl -s -o /dev/null -w '%{http_code}' -u "$NCU:$T" -H 'Host: localhost:8080' -X PROPFIND -H 'Depth: 0' http://127.0.0.1:8080/remote.php/dav/files/$NCU/)
echo "token len=${#T} direct test=$C"
if [ "$C" = 207 ]; then
  sed -i '/^NEXTCLOUD_APP_PASSWORD=/d' .env && printf 'NEXTCLOUD_APP_PASSWORD=%s\n' "$T" >> .env
  echo "saved; lines=$(grep -c '^NEXTCLOUD_APP_PASSWORD=' .env)"
  docker compose up -d nextcloud-ro 2>&1 | tail -1; sleep 4
  echo "--- ncfiles ls:"; docker exec -u claude claude-box ncfiles ls | head -20
else
  echo "--- occ said (redacted):"; printf '%s\n' "$O" | sed -E 's/[A-Za-z0-9]{5}(-[A-Za-z0-9]{5}){4}/<redacted>/g; s/[A-Za-z0-9]{40,}/<redacted>/g' | tail -6
fi
unset T O C
