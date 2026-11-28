#!/bin/bash
# Build the workflows with your private settings from env.local.sh (not in git), then optionally deploy.
# usage: ./make.sh [deploy]
set -euo pipefail
cd "$(dirname "$0")"
[ -f env.local.sh ] && source env.local.sh
python3 build_all.py
[ "${1:-}" = deploy ] && ./deploy.sh
