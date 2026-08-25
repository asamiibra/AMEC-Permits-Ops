#!/usr/bin/env bash
set -euo pipefail

: "${T3_NAS_IP:?Set the verified NAS LAN IPv4 address; do not use a hostname}"
: "${T3_CONTROL_DIR:?Set the isolated T3 control directory}"
: "${T3_EVIDENCE_DIR:?Set the writable T3 evidence directory}"
: "${T3_IMAGE_TAR:?Set the immutable image tar path}"
: "${T3_IMAGE_REF:?Set the exact image reference}"

share="ProposalOps-T3-Synthetic"
root="cert/v1"
run_id="${T3_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
missing_share="ProposalOps-T3-Missing-${run_id}"
ro_secret="$T3_CONTROL_DIR/t3_ro.secret"
denied_secret="$T3_CONTROL_DIR/t3_denied.secret"
pre_state="$T3_CONTROL_DIR/10_DSM_PRE_STATE.json"
fixture_manifest="$T3_CONTROL_DIR/13_FIXTURE_MANIFEST.json"

cleanup() { rm -f -- "$ro_secret" "$denied_secret"; }
trap cleanup EXIT HUP INT TERM

test -f "$ro_secret" && test -f "$denied_secret" && test -f "$pre_state" && test -f "$fixture_manifest"
test "$(stat -f '%Lp' "$ro_secret" 2>/dev/null || stat -c '%a' "$ro_secret")" = "600"
test "$(stat -f '%Lp' "$denied_secret" 2>/dev/null || stat -c '%a' "$denied_secret")" = "600"
mkdir -p "$T3_EVIDENCE_DIR"
docker load --input "$T3_IMAGE_TAR" >/dev/null
docker run --rm \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --network=bridge \
  --mount "type=bind,src=$T3_EVIDENCE_DIR,dst=/evidence,rw" \
  --mount "type=bind,src=$pre_state,dst=/control/10_DSM_PRE_STATE.json,ro" \
  --mount "type=bind,src=$fixture_manifest,dst=/control/13_FIXTURE_MANIFEST.json,ro" \
  --mount "type=bind,src=$ro_secret,dst=/run/secrets/t3_ro.secret,ro" \
  --mount "type=bind,src=$denied_secret,dst=/run/secrets/t3_denied.secret,ro" \
  "$T3_IMAGE_REF" \
  python3 -m scripts.synology_t3.t3_runner \
    --nas-ip "$T3_NAS_IP" --share "$share" --root "$root" --missing-share "$missing_share" \
    --pre-state /control/10_DSM_PRE_STATE.json --fixture-manifest /control/13_FIXTURE_MANIFEST.json \
    --evidence-root /evidence --image-revision "$T3_IMAGE_REF"

echo "T3_CONTAINER_EXIT=0"
echo "T3_SECRET_FILES_RETAINED=0"
echo "T3_RECURRING_TASKS_ENABLED=0"
