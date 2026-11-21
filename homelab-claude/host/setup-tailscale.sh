#!/usr/bin/env bash
# Run once on the Debian host as root. Joins the tailnet with Tailscale SSH and publishes the
# local-only services to YOUR TAILNET ONLY over HTTPS. Never use `tailscale funnel` here:
# funnel = public internet.
set -euo pipefail

command -v tailscale >/dev/null || curl -fsSL https://tailscale.com/install.sh | sh

# --ssh: SSH authenticated by your Tailscale identity (no keys/passwords to manage, no port 22 on LAN)
tailscale up --ssh --hostname="${TS_HOSTNAME:-homelab}" --advertise-tags=tag:homelab

# Tailnet-only HTTPS (Tailscale issues the certificate). Serve accepts ports 443, 8443, 10000.
tailscale serve --bg --https=443   http://127.0.0.1:7681   # web terminal (ttyd -> tmux "main")
tailscale serve --bg --https=8443  http://127.0.0.1:3000   # Grafana
tailscale serve --bg --https=10000 http://127.0.0.1:5678   # n8n (only if you use the n8n profile)
tailscale serve status

install -m 755 "$(dirname "$0")/cc" /usr/local/bin/cc
echo "Done. From any of your devices: https://$(tailscale status --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
