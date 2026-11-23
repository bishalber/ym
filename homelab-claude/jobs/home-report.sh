#!/usr/bin/env bash
# Daily Home Assistant report. Loads ONLY the Home Assistant MCP server and allows ONLY its
# read tool (GetLiveContext), so this job can look but never switch anything.
source "$(dirname "$0")/_lib.sh"

if [[ -z "${HA_URL:-}" || -z "${HA_TOKEN:-}" ]]; then
  echo "HA_URL / HA_TOKEN not set in .env" >&2
  exit 3
fi

cd /workspace/home 2>/dev/null || cd /workspace
MCP=home ALLOW="mcp__homeassistant__GetLiveContext" TURNS=4 \
  MODEL="${MODEL:-haiku}" run_claude \
"استخدم GetLiveContext واكتبلي تقرير قصير عن البيت بالعامية المصرية:
أجهزة offline أو unavailable، بطاريات تحت 20%، حساسات بقراءات غريبة، وأي حاجة سايبة مفتوحة أو شغالة من غير داعي.
6 نقاط بالكتير. لو كله تمام قول: البيت تمام ✅" </dev/null
