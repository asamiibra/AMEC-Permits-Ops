#!/usr/bin/env bash
set -euo pipefail
: "${T3_HANDOFF_DIR:?Set the immutable accepted handoff directory}"
test -d "$T3_HANDOFF_DIR/fixture_staging/cert/v1"
test -f "$T3_HANDOFF_DIR/13_FIXTURE_MANIFEST.json"
result="$(python3 -B "$T3_HANDOFF_DIR/fixture_manifest.py" --manifest "$T3_HANDOFF_DIR/13_FIXTURE_MANIFEST.json" --verify-staged-root "$T3_HANDOFF_DIR/fixture_staging")"
printf '%s\n' "$result"
python3 -B - "$result" <<'PY'
import json, sys
result = json.loads(sys.argv[1])
if result.get("status") != "PASS" or result.get("fixture_count") != 270 or result.get("fixture_regeneration_executed") is not False:
    raise SystemExit("STOP_T3_SHIPPED_FIXTURE_STAGING_MISMATCH")
PY
echo "T3_SHIPPED_FIXTURE_STAGING_VERIFIED=PASS"
echo "FIXTURE_COUNT=270"
echo "FIXTURE_REGENERATION_EXECUTED=false"
