#!/bin/bash
# One-time transfer of the teacher's lessons, skill, prompt and metadata into Nextcloud (WebDAV).
# Needs:  NC_URL=https://cloud.example.com   NC_USER=bishu   NC_APP_PASSWORD=<Nextcloud app password>
# Create the app password in Nextcloud: Settings > Security > Devices & sessions. Never reuse your login password.
# vocab.json / notes.json are NOT overwritten if they already exist (they hold your live progress); FORCE=1 overrides.
set -euo pipefail
: "${NC_URL:?set NC_URL}" "${NC_USER:?set NC_USER}" "${NC_APP_PASSWORD:?set NC_APP_PASSWORD}"
cd "$(dirname "$0")"
BASE="${NC_URL%/}/remote.php/dav/files/$NC_USER/FinnishBot"
AUTH=(-u "$NC_USER:$NC_APP_PASSWORD")
mk() { code=$(curl -sS -o /dev/null -w '%{http_code}' "${AUTH[@]}" -X MKCOL "$BASE/$1"); echo "MKCOL $1 -> $code"; }
put() { # <local> <remote>
  if [[ "$2" =~ ^(vocab|notes)\.json$ && "${FORCE:-0}" != 1 ]]; then
    h=$(curl -sS -o /dev/null -w '%{http_code}' "${AUTH[@]}" -I "$BASE/$2")
    if [ "$h" = 200 ]; then echo "skip $2 (exists; FORCE=1 to overwrite)"; return; fi
  fi
  code=$(curl -sS -o /dev/null -w '%{http_code}' "${AUTH[@]}" -T "$1" "$BASE/$2"); echo "PUT  $2 -> $code"
}
mk ""; for d in lessons notes homework skill meta; do mk "$d"; done
put nextcloud/vocab.json vocab.json
put nextcloud/notes.json notes.json
put ../.claude/skills/teacher/SKILL.md skill/teacher-SKILL.md
put ../finnish-teacher-agent.md skill/finnish-teacher-agent-portable.md
put src/teacher_prompt.md skill/bot-system-prompt.md
put src/facts.md meta/learner-facts.md
put nextcloud/meta/progress-notes.md meta/progress-notes.md
put nextcloud/meta/session-log.md meta/session-log.md
put nextcloud/lessons/2026-11-20-telling-time.md lessons/2026-11-20-telling-time.md
echo "Done. 201 = created, 204 = overwritten, 405 on MKCOL = folder already exists."
