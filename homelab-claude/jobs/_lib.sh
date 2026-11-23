#!/usr/bin/env bash
# Shared, token-frugal defaults for every automated job. Source it, then call run_claude.
#
#   MODEL=haiku TURNS=1 TOOLS="" MCP=none ALLOW="" run_claude "prompt"    (stdin passes through)
#
# Defaults are the cheapest possible call:
#   - model haiku (override per job: MODEL=sonnet)
#   - 1 agentic turn, NO built-in tools (TOOLS="Read,Grep,Glob" to grant some)
#   - NO MCP servers (MCP=home loads only jobs/mcp/home.json). Tool definitions from connectors
#     and MCP servers are sent with every request; a bare "hi" measured ~45k context tokens with
#     a full connector set loaded, so jobs start from an empty set on purpose.
#   - dontAsk: anything not pre-approved is denied instead of waiting for a human
set -euo pipefail

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ANTHROPIC_API_KEY is set: claude -p would bill the API instead of Claude Pro. Unset it." >&2
  exit 2
fi

JOBS_HOME="${JOBS_HOME:-/opt/claude-jobs}"

run_claude() {
  local prompt="$1"
  local mcp_file="${JOBS_HOME}/mcp/${MCP:-none}.json"
  local args=(
    -p "$prompt"
    --model "${MODEL:-${JOB_MODEL:-haiku}}"
    --max-turns "${TURNS:-1}"
    --output-format json
    --permission-mode dontAsk
    --strict-mcp-config --mcp-config "$mcp_file"
    --tools "${TOOLS-}"
  )
  if [[ -n "${ALLOW:-}" ]]; then args+=(--allowedTools "$ALLOW"); fi
  claude "${args[@]}"
}
