#!/usr/bin/env bash
# Run ON THE HOST with sudo:  sudo bash host/backup-setup.sh
# Sets up the nightly encrypted restic backup of /srv/claude + the stack folder, into
# /var/backups/claude-restic on this machine (same disk as /: protects against mistakes and bad
# updates, NOT against the disk dying). Prints the repository password ONCE: save it elsewhere.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
STACK="${STACK_DIR:-/opt/homelab-claude}"
command -v restic >/dev/null || apt-get install -y restic
install -m 755 "$HERE/backup.sh" /usr/local/bin/claude-backup
NEW=0
if [ ! -f /etc/claude-backup.env ]; then
  NEW=1; PW="$(openssl rand -base64 32)"
  NT="$(grep -m1 '^NTFY_RUNNER_TOKEN=' "$STACK/.env" | cut -d= -f2- || true)"
  umask 077
  cat > /etc/claude-backup.env <<E
RESTIC_REPOSITORY=/var/backups/claude-restic
RESTIC_PASSWORD=$PW
DATA_ROOT=/srv/claude
STACK_DIR=$STACK
NTFY_URL=http://127.0.0.1:2586/claude-jobs
NTFY_TOKEN=$NT
NTFY_ON_OK=0
E
fi
cp "$HERE"/claude-backup.service "$HERE"/claude-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now claude-backup.timer
claude-backup && echo "first backup OK" || { echo "FIRST BACKUP FAILED"; exit 1; }
set -a; . /etc/claude-backup.env; set +a
restic snapshots --compact | tail -4; du -sh "$RESTIC_REPOSITORY"
systemctl list-timers claude-backup.timer --no-pager | head -2
if [ "$NEW" = 1 ]; then echo; echo "=== SAVE THIS PASSWORD OFF THIS SERVER (password manager). Shown once: ==="; echo "$PW"; fi
