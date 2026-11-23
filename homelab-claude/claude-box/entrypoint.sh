#!/usr/bin/env bash
# Starts the three long-lived pieces of claude-box:
#   tmux "main"  : window "work" (your shell) + window "rc" (Claude Remote Control server)
#   ttyd :7681   : browser terminal that attaches to the same tmux session
#   runner :8787 : automation endpoint for n8n (whitelisted jobs only)
set -euo pipefail

# First start: seed user-level settings once; afterwards they are yours to edit.
mkdir -p "$HOME/.claude" /var/log/claude 2>/dev/null || true
for f in settings.json CLAUDE.md; do
  [ -f "$HOME/.claude/$f" ] || cp "/opt/home-template/$f" "$HOME/.claude/$f"
done

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "WARNING: ANTHROPIC_API_KEY is set; headless runs would bill the API, not Claude Pro." >&2
fi

SESSION=main
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux new-session -d -s "$SESSION" -n work -c /workspace
  # Remote Control server: needs a one-time `claude` + /login in the "work" window first.
  tmux new-window -d -t "$SESSION" -n rc -c /workspace \
    'while true; do claude remote-control --name "${CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX:-homelab}"; \
       echo "[rc] exited. If not logged in: run claude in window 0 and /login. Retrying in 60s"; sleep 60; done'
fi

claude-runner &
ttyd --writable --port 7681 --interface 0.0.0.0 \
     -t titleFixed="claude@${CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX:-homelab}" \
     tmux new-session -A -s "$SESSION" &

# If either service dies, exit so Docker's restart policy brings the box back cleanly.
wait -n
echo "a service exited; restarting container" >&2
exit 1
