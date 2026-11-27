#!/bin/bash
# Import + publish all BishuFinnish_bot workflows into a Docker-hosted n8n (Agent Foundry Playbook, step 11).
# Tools first (the chat workflow calls them), then chat, daily lesson and evening review.
# usage: ./deploy.sh            (container name: N8N_CONTAINER, default n8n-n8n-1)
set -euo pipefail
C="${N8N_CONTAINER:-n8n-n8n-1}"
cd "$(dirname "$0")"
deploy() {  # <build-json> <workflow-id>
  docker cp "build/$1" "$C:/tmp/deploy.json"
  docker exec "$C" n8n import:workflow --input=/tmp/deploy.json
  docker exec "$C" n8n publish:workflow --id="$2"
}
deploy tool_vocab_add.json   FItoolVocabAdd01
deploy tool_vocab_due.json   FItoolVocabDue01
deploy tool_vocab_grade.json FItoolVocabGrd01
deploy tool_remember.json    FItoolRemember01
deploy tool_save_file.json   FItoolSaveFile01
deploy chat.json             FIchat0000000001
deploy daily_lesson.json     FIdaily000000001
deploy evening_review.json   FIreview00000001
echo "Done. Publishing applies in ~20 s. Open n8n and check the 3 credentials are attached (Telegram, Anthropic, Nextcloud)."
