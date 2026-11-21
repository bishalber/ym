#!/usr/bin/env bash
# Generic "summarize whatever n8n sends me" job: haiku, one turn, no tools, no MCP.
# n8n: HTTP Request -> POST http://claude-box:8787/run/summarize, body = the text.
source "$(dirname "$0")/_lib.sh"

MODEL="${MODEL:-haiku}" TURNS=1 run_claude \
"لخّص النص اللي جاي (من stdin) بالعامية المصرية في 5 نقاط بالكتير.
لو فيه حاجة محتاجة تصرّف مني، ابدأ السطر الأول بـ: ⚠️ مطلوب تصرّف.
ماتضيفش مقدمة ولا خاتمة."
