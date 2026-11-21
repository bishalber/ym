#!/usr/bin/env bash
# Encrypted, deduplicated backup of everything Claude-related, kept on this Debian homelab.
# /etc/claude-backup.env (chmod 600) must define:
#   RESTIC_REPOSITORY=/var/backups/claude-restic   (on this server, OUTSIDE $DATA_ROOT.
#                                                   A second disk mounted here is better: same
#                                                   disk = no protection if that disk dies)
#   RESTIC_PASSWORD=...                            (keep a copy OFF this server, e.g. password manager)
#   DATA_ROOT=/srv/claude
#   STACK_DIR=/opt/homelab-claude                  (this folder, incl. your .env)
# Optional, to get a phone notification when a backup fails (same ntfy as the jobs):
#   NTFY_URL=http://127.0.0.1:2586/claude-jobs
#   NTFY_TOKEN=tk_...                              (the NTFY_RUNNER_TOKEN from .env)
#   NTFY_ON_OK=0                                   (1 = also notify on success)
set -euo pipefail
set -a; source /etc/claude-backup.env; set +a

notify() {  # notify <title> <message> <priority> <tag>; never fails the backup itself
  [[ -n "${NTFY_URL:-}" ]] || return 0
  curl -fsS -m 10 -o /dev/null -H "Title: $1" -H "Priority: $3" -H "Tags: $4" \
       ${NTFY_TOKEN:+-H "Authorization: Bearer $NTFY_TOKEN"} -d "$2" "$NTFY_URL" || true
}
trap 'notify "claude-backup failed" "Step failed at line $LINENO on $(hostname). Check: journalctl -u claude-backup" high x' ERR

case "$RESTIC_REPOSITORY" in
  "$DATA_ROOT"|"$DATA_ROOT"/*)
    echo "RESTIC_REPOSITORY must be outside $DATA_ROOT" >&2
    notify "claude-backup misconfigured" "RESTIC_REPOSITORY is inside $DATA_ROOT; no backup was made." high x
    exit 2 ;;
esac
if [[ "$RESTIC_REPOSITORY" == /* ]]; then mkdir -p "$RESTIC_REPOSITORY"; chmod 700 "$RESTIC_REPOSITORY"; fi

restic cat config >/dev/null 2>&1 || restic init

# Prometheus TSDB is skipped (rebuildable, large); n8n, ntfy and Grafana DBs are included.
restic backup "$DATA_ROOT" "$STACK_DIR" \
  --exclude "$DATA_ROOT/prometheus" \
  --exclude "**/node_modules" \
  --tag claude

restic forget --tag claude --keep-daily 7 --keep-weekly 5 --keep-monthly 12 --prune
restic check --read-data-subset=2%

if [[ "${NTFY_ON_OK:-0}" == 1 ]]; then
  notify "claude-backup ok" "$(restic snapshots --tag claude --latest 1 --compact | tail -n 3 | head -n 1)" low floppy_disk
fi
