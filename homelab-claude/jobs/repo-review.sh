#!/usr/bin/env bash
# Nightly review of the last 24h of commits in every git repo under /workspace.
# The script gathers and trims the diffs itself, so Claude gets ONE prompt and needs no tools:
# no repo exploration, no tool loop, predictable cost.
source "$(dirname "$0")/_lib.sh"

SINCE="${SINCE:-24 hours ago}"
MAX_LINES_PER_REPO="${MAX_LINES_PER_REPO:-1200}"
EXCLUDES=(':(exclude)*.lock' ':(exclude)package-lock.json' ':(exclude)*.min.*' ':(exclude)dist/*')

bundle=""
while IFS= read -r gitdir; do
  repo="$(dirname "$gitdir")"
  changes="$(git -C "$repo" log --since="$SINCE" --no-merges -p --stat \
              --pretty='--- %h %an: %s' -- . "${EXCLUDES[@]}" 2>/dev/null \
              | head -n "$MAX_LINES_PER_REPO" || true)"
  [[ -z "$changes" ]] && continue
  bundle+=$'\n\n### '"${repo#/workspace/}"$'\n'"$changes"
done < <(find /workspace -maxdepth 3 -type d -name .git 2>/dev/null)

if [[ -z "$bundle" ]]; then
  # Same shape as claude's JSON so the runner logs it as a zero-token run.
  echo '{"type":"result","result":"لا توجد commits جديدة","usage":{},"num_turns":0}'
  exit 0
fi

printf '%s' "$bundle" | MODEL="${MODEL:-sonnet}" TURNS=1 run_claude \
"راجع الـ commits اللي في stdin (آخر 24 ساعة). رد بالعامية المصرية، 10 نقاط بالكتير، مرتبة بالخطورة:
bugs محتملة، مشاكل أمان، تغييرات خطيرة أو ناقصة tests. اذكر الريبو والـ commit hash في كل نقطة.
لو مفيش حاجة مهمة قول: تمام ✅ بس."
