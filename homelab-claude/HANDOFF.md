# Homelab Claude setup: handoff (state as of 2026-11-23)

Public repo: keep personal names, IPs and tailnet names OUT of this file (use placeholders).

## Where things are
- Repo: `/workspace/ym` (branch `claude/trusting-knuth-q8ho0v`, draft PR #2 of the owner's `ym` repo). The stack lives in `homelab-claude/`; this file is `homelab-claude/HANDOFF.md`. PLAN.md (Egyptian Arabic) is the full plan.
  The stack lives in `homelab-claude/`. PLAN.md (Egyptian Arabic) is the full plan.
- Deployed copy on the host: `/opt/homelab-claude` (has `.env`, chmod 600, and `docker-compose.override.yml`, both NOT in git).
  Host update flow: `git -C ~/ym-homelab pull && cp -r ~/ym-homelab/homelab-claude/. /opt/homelab-claude/ && cd /opt/homelab-claude && docker compose up -d --build`
- Host: Debian homelab host, 7.5 GB RAM, tailnet name `<server>.<tailnet>.ts.net`, user uid 1000.

## What runs (all done and working)
- `claude-box` (this container): tmux `main` with `work` + `rc` (Remote Control, shows as "workspace · <hostname>" in the Claude app), ttyd :7681, runner :8787. Mem cap 1.5 GB.
- `claude-grafana` (384 MB), `claude-prometheus` (384 MB), `claude-otel` (192 MB), `claude-ntfy` (96 MB), `claude-nextcloud-ro` (64 MB).
- Tailscale serve (tailnet only): :8449 web terminal, :8450 Grafana, :2586 ntfy. Existing serve ports untouched:
  :443 Nextcloud, :8443 FUNNEL (n8n webhooks, public), :8444-8448 other apps. Never reuse those.
- Tailscale SSH on (`ssh <server>` from the owner's PC works, check mode). ACL = default policy, unchanged.
- Read-only mounts in this container: `/data/shared` (=/mnt/homelab/shared), `/data/windows` (=/mnt/windows), `/data/DATA` (=/DATA, AppData hidden by tmpfs).
- n8n already runs separately (`n8n-n8n-1`); our compose n8n stays behind `--profile n8n` (do not start it).

## Decisions taken
- Read-only everywhere by default. Nextcloud server-side encryption is ON, so Nextcloud is read via WebDAV through `nextcloud-ro` (holds the app password; this container never sees it). Tool here: `ncfiles ls|find|get|cat`.
- Memory: host was OOMing. Done: Paperclip service disabled, Checkmk (`omd`) disabled, 4 GB /swapfile added (swap now 5 GB), every claude-* container capped.
  RULE: never run `claude` directly on the host; use this container (app "workspace · <hostname>" or `cc`).

## Open items (in order)
1. Nextcloud app password: NOT set yet (`.env` has a wrong 9-char value; `ncfiles` returns 401).
   Run ON THE HOST (needs docker): `bash /opt/homelab-claude/host/nextcloud-token.sh`
   It creates app password `claude-ro` for `$NEXTCLOUD_USER` (set in `.env`) without a login password (encryption uses the default master key),
   tests it (expects 207), saves it to /opt/homelab-claude/.env, restarts nextcloud-ro and runs `ncfiles ls`. It never prints the token.
   Then verify a real download decrypts: `ncfiles find .pdf` then `ncfiles get <path>` and check it does not start with `HBEGIN:oc_encryption`.
   If GET fails while ls works, master key is off: create the app password in the Nextcloud UI instead (Settings > Security).
2. ntfy: create user + token (`docker exec -it claude-ntfy ntfy user add --role=admin me`, `ntfy token add me`), put token in `NTFY_RUNNER_TOKEN`, subscribe phone app to `https://<server>.<tailnet>.ts.net:2586/claude-jobs`.
3. Connect existing n8n to `claude-net` (add the external network to n8n's own compose), then schedule jobs via `http://claude-box:8787/run/<job>`.
4. Home Assistant runs as container `homeassistant`; set `HA_URL`/`HA_TOKEN` in .env if wanted.
5. Backup (PLAN.md phase 6) not installed yet: restic to /var/backups/claude-restic on this host.
6. "Homelab" claude.ai connector returns 502: not investigated.
7. An orphan rsync job from an earlier host-side Claude session may still be running: check with `pgrep -a rsync` on the host before assuming it is done.

## Limits of this container
- No docker socket and no sudo here: host changes (docker compose, occ, systemctl) must be run on the host by the owner (or via Desktop Commander).
- No GitHub credentials here: commits to the repo need pushing from a session that has them.
