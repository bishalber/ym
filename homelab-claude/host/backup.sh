#!/usr/bin/env bash
# Encrypted, deduplicated backup of everything Claude-related on the homelab.
# /etc/claude-backup.env (chmod 600) must define:
#   RESTIC_REPOSITORY=/mnt/backupdisk/claude-restic   (2nd disk, NAS, or sftp:user@nas:/path)
#   RESTIC_PASSWORD=...                               (store a copy OFF this server!)
#   DATA_ROOT=/srv/claude
#   STACK_DIR=/opt/homelab-claude                     (this folder, incl. your .env)
set -euo pipefail
set -a; source /etc/claude-backup.env; set +a

restic snapshots >/dev/null 2>&1 || restic init

# Prometheus TSDB is skipped (rebuildable, large); n8n and Grafana DBs are included.
restic backup "$DATA_ROOT" "$STACK_DIR" \
  --exclude "$DATA_ROOT/prometheus" \
  --exclude "**/node_modules" \
  --tag claude

restic forget --tag claude --keep-daily 7 --keep-weekly 5 --keep-monthly 12 --prune
restic check --read-data-subset=2%
