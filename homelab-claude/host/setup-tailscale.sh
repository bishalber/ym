#!/usr/bin/env bash
# Run once on the Debian host as root. Safe on a machine that is ALREADY in your tailnet and
# already serves other apps: it changes no hostname, no tags and no existing serve/funnel port.
#   1. turns on Tailscale SSH (only this one setting; `tailscale set` leaves every other pref alone)
#   2. publishes the claude stack to YOUR TAILNET ONLY on ports nothing else uses
# Never use `tailscale funnel` for these: funnel = public internet.
set -euo pipefail

TTYD_PORT="${TTYD_PORT:-8449}"       # web terminal (ttyd -> tmux "main")
GRAFANA_PORT="${GRAFANA_PORT:-8450}" # Grafana
NTFY_PORT="${NTFY_PORT:-2586}"       # ntfy (phone app subscribes here)

command -v tailscale >/dev/null || { echo "tailscale is not installed" >&2; exit 1; }

# Refuse to touch a port that already serves something (Nextcloud, n8n funnel, ...).
current="$(tailscale serve status 2>/dev/null || true)"
for p in "$TTYD_PORT" "$GRAFANA_PORT" "$NTFY_PORT"; do
  pat="\.ts\.net:${p}( |$)"; [[ "$p" == 443 ]] && pat="\.ts\.net(:443)?( |$)"  # 443 is shown without a port
  if grep -qE "$pat" <<<"$current"; then
    echo "Port $p is already used by tailscale serve/funnel. Pick another (e.g. TTYD_PORT=...)." >&2
    exit 1
  fi
done

# SSH authenticated by your Tailscale identity. Plain OpenSSH on the LAN keeps working.
tailscale set --ssh

# Tailnet-only HTTPS (Tailscale issues the certificate). The 443/8443/10000 limit is a Funnel rule;
# Serve takes any port.
tailscale serve --bg --https="$TTYD_PORT"    http://127.0.0.1:7681
tailscale serve --bg --https="$GRAFANA_PORT" http://127.0.0.1:3000
tailscale serve --bg --https="$NTFY_PORT"    http://127.0.0.1:2586
tailscale serve status

install -m 755 "$(dirname "$0")/cc" /usr/local/bin/cc
fqdn="$(tailscale status --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
echo
echo "Done. Put this in .env:  TS_FQDN=$fqdn"
echo "  web terminal: https://$fqdn:$TTYD_PORT"
echo "  Grafana:      https://$fqdn:$GRAFANA_PORT"
echo "  ntfy:         https://$fqdn:$NTFY_PORT"
