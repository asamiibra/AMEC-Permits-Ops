#!/usr/bin/env bash
set -euo pipefail
: "${T3_CONTROL_DIR:?Set the isolated T3 control directory}"
mkdir -p "$T3_CONTROL_DIR/fixture_staging"
python3 "$(dirname "$0")/fixture_manifest.py" --output-root "$T3_CONTROL_DIR/fixture_staging" --manifest "$T3_CONTROL_DIR/13_FIXTURE_MANIFEST.json"
echo "Fixture staging created at $T3_CONTROL_DIR/fixture_staging"
echo "Upload only this generated cert/v1 tree into the dedicated synthetic share via DSM File Station."
