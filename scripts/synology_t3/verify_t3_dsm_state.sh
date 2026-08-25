#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
: "${1:?Usage: verify_t3_dsm_state.sh pre|post state.json}"
: "${2:?Usage: verify_t3_dsm_state.sh pre|post state.json}"
python3 -B "$(dirname "$0")/dsm_state_schema.py" \
  --phase "$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')" \
  "$2"
