#!/usr/bin/env bash
set -euo pipefail
stop() { printf '%s\n' "$1" >&2; exit 2; }
HOST_EUID="$(id -u)"
test "$HOST_EUID" = 0 || stop STOP_T3_OWNER_WRAPPER_NOT_ROOT
export PYTHONDONTWRITEBYTECODE=1
: "${T3_HANDOFF_DIR:?Set the immutable downloaded handoff directory}"
: "${T3_IMAGE_TAR:?Set the immutable image tar path}"
T3_CONTROL_ROOT="${T3_CONTROL_ROOT:-/volume1/ProposalOps-Inventory}"
test "$T3_CONTROL_ROOT" = "/volume1/ProposalOps-Inventory" || stop STOP_T3_CONTROL_ROOT_DRIFT
test -d "$T3_CONTROL_ROOT" && test ! -L "$T3_CONTROL_ROOT" || stop STOP_T3_CONTROL_ROOT_DRIFT
run_id="${T3_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
T3_CONTROL_DIR="${T3_CONTROL_DIR:-$T3_CONTROL_ROOT/SYN-T3/$run_id}"
T3_EVIDENCE_DIR="${T3_EVIDENCE_DIR:-$T3_CONTROL_DIR/evidence}"
root_real="$(cd "$T3_CONTROL_ROOT" && pwd -P)"
dir_real="$(readlink -f "$T3_CONTROL_DIR" 2>/dev/null || true)"
case "$dir_real" in "$root_real"/*) ;; *) stop STOP_T3_CONTROL_ROOT_ESCAPE ;; esac
test -d "$T3_CONTROL_DIR" && test ! -L "$T3_CONTROL_DIR" || stop STOP_T3_CONTROL_ROOT_DRIFT
test "$(stat -c '%u:%g' "$T3_CONTROL_DIR" 2>/dev/null || stat -f '%u:%g' "$T3_CONTROL_DIR")" = "0:0" || stop STOP_T3_CONTROL_ROOT_DRIFT
test "$(stat -c '%a' "$T3_CONTROL_DIR" 2>/dev/null || stat -f '%Lp' "$T3_CONTROL_DIR")" = "700" || stop STOP_T3_CONTROL_ROOT_DRIFT
uid_collision=false; gid_collision=false
awk -F: '$3 == 10001 { found=1 } END { exit(found ? 0 : 1) }' /etc/passwd && uid_collision=true || true
awk -F: '$3 == 10001 { found=1 } END { exit(found ? 0 : 1) }' /etc/group && gid_collision=true || true
test "$uid_collision" = false && test "$gid_collision" = false || stop STOP_T3_HOST_UID_GID_COLLISION
mkdir -p "$T3_EVIDENCE_DIR"; chown 10001:10001 "$T3_EVIDENCE_DIR"; chmod 700 "$T3_EVIDENCE_DIR"
evidence_owner="$(stat -c '%u:%g' "$T3_EVIDENCE_DIR" 2>/dev/null || stat -f '%u:%g' "$T3_EVIDENCE_DIR")"
evidence_mode="$(stat -c '%a' "$T3_EVIDENCE_DIR" 2>/dev/null || stat -f '%Lp' "$T3_EVIDENCE_DIR")"
test "$evidence_owner" = "10001:10001" && test "$evidence_mode" = "700" || stop STOP_T3_EVIDENCE_DIR_POLICY
ro_secret="$T3_CONTROL_DIR/t3_ro.secret"; denied_secret="$T3_CONTROL_DIR/t3_denied.secret"
pre_state="$T3_CONTROL_DIR/10_DSM_PRE_STATE.json"; policy_file="$T3_HANDOFF_DIR/06_IMAGE_BUILD_POLICY.json"
preflight="$T3_HANDOFF_DIR/preflight_t3_handoff.py"
test -f "$policy_file" && test -f "$preflight" && test -f "$T3_HANDOFF_DIR/13_FIXTURE_MANIFEST.json" || stop STOP_T3_HANDOFF_OR_IMAGE_IDENTITY_MISMATCH
cleanup() { rm -f -- "$ro_secret" "$denied_secret"; test -z "${canary_dir:-}" || rm -rf -- "$canary_dir"; }
trap cleanup EXIT HUP INT TERM
if test "${T3_BOOTSTRAP_ONLY:-0}" = 1; then
  printf 'synthetic-bootstrap-ro\n' > "$ro_secret"; printf 'synthetic-bootstrap-denied\n' > "$denied_secret"
else
  test -f "$ro_secret" && test -f "$denied_secret" || stop STOP_T3_SECRET_FILE_POLICY
fi
for secret in "$ro_secret" "$denied_secret"; do
  test -f "$secret" && test ! -L "$secret" && test -s "$secret" || stop STOP_T3_SECRET_FILE_POLICY
  chown 10001:10001 "$secret"; chmod 600 "$secret"
done
secret_owner="$(stat -c '%u:%g' "$ro_secret" 2>/dev/null || stat -f '%u:%g' "$ro_secret")"
secret_mode="$(stat -c '%a' "$ro_secret" 2>/dev/null || stat -f '%Lp' "$ro_secret")"
test "$secret_owner" = "10001:10001" && test "$secret_mode" = "600" || stop STOP_T3_SECRET_FILE_POLICY
count_pyc() { find "$T3_HANDOFF_DIR" -type f -name '*.pyc' -print 2>/dev/null | wc -l | tr -d ' '; }
count_pycache() { find "$T3_HANDOFF_DIR" -type d -name '__pycache__' -print 2>/dev/null | wc -l | tr -d ' '; }
assert_clean() { test "$(count_pyc)" = 0 && test "$(count_pycache)" = 0 || stop STOP_T3_HANDOFF_BYTECODE_CONTAMINATION; }
manifest_digest() { shasum -a 256 "$T3_HANDOFF_DIR/MANIFEST.sha256" 2>/dev/null | awk '{print $1}' || sha256sum "$T3_HANDOFF_DIR/MANIFEST.sha256" | awk '{print $1}'; }
assert_clean; manifest_before="$(manifest_digest)"
policy_ref="$(python3 -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_ref"])' "$policy_file")"
preflight_result="$(python3 -B "$preflight" --handoff-root "$T3_HANDOFF_DIR" --image-tar "$T3_IMAGE_TAR" --image-ref "$policy_ref")"
assert_clean; manifest_after="$(manifest_digest)"
test "$manifest_before" = "$manifest_after" || stop STOP_T3_HANDOFF_BYTECODE_CONTAMINATION
fixture_result="$(python3 -B "$T3_HANDOFF_DIR/fixture_manifest.py" --manifest "$T3_HANDOFF_DIR/13_FIXTURE_MANIFEST.json" --verify-staged-root "$T3_HANDOFF_DIR/fixture_staging")"
printf '%s\n' "$fixture_result"
fixture_status="$(python3 -B -c 'import json,sys; print(json.loads(sys.argv[1])["status"])' "$fixture_result")"
test "$fixture_status" = PASS || stop STOP_T3_SHIPPED_FIXTURE_STAGING_MISMATCH
image_ref="$policy_ref"; harness_sha="$(python3 -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["harness_sha"])' "$policy_file")"
canary_dir="$T3_CONTROL_DIR/.bind-canary-$run_id"; mkdir "$canary_dir" "$canary_dir/evidence"
printf 'synthetic-bind-canary\n' > "$canary_dir/input.txt"; chown -R 10001:10001 "$canary_dir"; chmod 700 "$canary_dir" "$canary_dir/evidence"; chmod 600 "$canary_dir/input.txt"
canary_output="$(docker run --rm --network=none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m --cap-drop=ALL --security-opt=no-new-privileges --mount "type=bind,src=$canary_dir,dst=/canary" "$image_ref" python3 -B -c 'import json,os; from pathlib import Path; p=Path("/canary/input.txt"); data=p.read_text(); Path("/canary/output.txt").write_text(data+"written"); Path("/canary/evidence/canary.txt").write_text("synthetic"); print(json.dumps({"euid":os.geteuid(),"egid":os.getegid(),"read":data=="synthetic-bind-canary\n","write":Path("/canary/output.txt").is_file(),"reread":Path("/canary/output.txt").read_text()==data+"written"}))')"
canary_euid="$(python3 -B -c 'import json,sys; print(json.loads(sys.argv[1])["euid"])' "$canary_output")"; canary_egid="$(python3 -B -c 'import json,sys; print(json.loads(sys.argv[1])["egid"])' "$canary_output")"
canary_read="$(python3 -B -c 'import json,sys; print("PASS" if json.loads(sys.argv[1])["read"] else "FAIL")' "$canary_output")"; canary_write="$(python3 -B -c 'import json,sys; print("PASS" if json.loads(sys.argv[1])["write"] else "FAIL")' "$canary_output")"; canary_reread="$(python3 -B -c 'import json,sys; print("PASS" if json.loads(sys.argv[1])["reread"] else "FAIL")' "$canary_output")"
test "$canary_euid" = 10001 && test "$canary_egid" = 10001 && test "$canary_read" = PASS && test "$canary_write" = PASS && test "$canary_reread" = PASS || stop STOP_T3_HOST_BIND_PERMISSION_CANARY
test "$(stat -c '%u:%g' "$canary_dir/output.txt" 2>/dev/null || stat -f '%u:%g' "$canary_dir/output.txt")" = "10001:10001" || stop STOP_T3_HOST_BIND_PERMISSION_CANARY
host_python_version="$(python3 -B -c 'import platform; print(platform.python_version())')"; host_python_gate="$(python3 -B -c 'import sys; print("PASS" if sys.version_info >= (3,8) and sys.dont_write_bytecode else "FAIL")')"
image_preexisting="$(python3 -B -c 'import json,sys; print(str(json.loads(sys.argv[1])["image_ref_preexisting"]).lower())' "$preflight_result")"; image_preexisting_exact="$(python3 -B -c 'import json,sys; print(str(json.loads(sys.argv[1])["image_ref_preexisting_exact"]).lower())' "$preflight_result")"; docker_load_count="$(python3 -B -c 'import json,sys; print(json.loads(sys.argv[1])["docker_load_count"])' "$preflight_result")"
python3 -B - "$T3_EVIDENCE_DIR/16_HOST_BOOTSTRAP.json" <<PY
import json, sys
payload = {"host_python_version":"$host_python_version","host_python_38_compatibility_gate":"$host_python_gate","python_dont_write_bytecode":True,"handoff_pyc_before":0,"handoff_pyc_after":0,"handoff_manifest_before":"$manifest_before","handoff_manifest_after":"$manifest_after","host_euid":$HOST_EUID,"uid_10001_collision":"$uid_collision" == "true","gid_10001_collision":"$gid_collision" == "true","control_root":"$T3_CONTROL_ROOT","control_dir_within_control_root":True,"control_dir_owner":"0:0","control_dir_mode":"0700","fixture_staging_verified":"$fixture_status","fixture_count":270,"fixture_regeneration_executed":False,"image_ref_preexisting":"$image_preexisting" == "true","image_ref_preexisting_exact":"$image_preexisting_exact" == "true","docker_load_count":$docker_load_count,"image_id_verified":True,"bind_canary_network_mode":"none","bind_canary_euid":$canary_euid,"bind_canary_egid":$canary_egid,"bind_canary_read":"$canary_read","bind_canary_write":"$canary_write","bind_canary_reread":"$canary_reread","secret_owner_uid":10001,"secret_owner_gid":10001,"secret_mode":"0600","evidence_owner_uid":10001,"evidence_owner_gid":10001,"evidence_mode":"0700","status":"PASS" if "$host_python_gate"=="PASS" and "$fixture_status"=="PASS" else "FAIL"}
json.dump(payload, open(sys.argv[1],"w"), indent=2, sort_keys=True); open(sys.argv[1],"a").write("\n")
PY
chown 10001:10001 "$T3_EVIDENCE_DIR/16_HOST_BOOTSTRAP.json"
if test "${T3_BOOTSTRAP_ONLY:-0}" = 1; then
  echo T3_BOOTSTRAP_ONLY_RESULT=PASS; echo BOOTSTRAP_ONLY_SMB_CONNECTIONS=0; echo BOOTSTRAP_ONLY_SYNOLOGY_CONNECTIONS=0; echo BOOTSTRAP_ONLY_DSM_API_CALLS=0; exit 0
fi
: "${T3_NAS_IP:?Set the freshly verified NAS LAN IPv4 address; do not use a hostname}"
share=ProposalOps-T3-Synthetic; root=cert/v1; missing_share="ProposalOps-T3-Missing-$run_id"
test -f "$pre_state" || stop STOP_T3_OWNER_WRAPPER_NOT_ROOT
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop=ALL --security-opt=no-new-privileges --network=bridge --mount "type=bind,src=$T3_EVIDENCE_DIR,dst=/evidence" --mount "type=bind,src=$pre_state,dst=/control/10_DSM_PRE_STATE.json,readonly" --mount "type=bind,src=$T3_HANDOFF_DIR/13_FIXTURE_MANIFEST.json,dst=/control/13_DSM_FIXTURE_MANIFEST.json,readonly" --mount "type=bind,src=$ro_secret,dst=/run/secrets/t3_ro.secret,readonly" --mount "type=bind,src=$denied_secret,dst=/run/secrets/t3_denied.secret,readonly" "$image_ref" python3 -B -m scripts.synology_t3.t3_runner --nas-ip "$T3_NAS_IP" --share "$share" --root "$root" --missing-share "$missing_share" --run-id "$run_id" --pre-state /control/10_DSM_PRE_STATE.json --fixture-manifest /control/13_DSM_FIXTURE_MANIFEST.json --evidence-root /evidence --image-revision "$harness_sha"
echo T3_CONTAINER_EXIT=0; echo T3_SECRET_FILES_RETAINED=0; echo T3_RECURRING_TASKS_ENABLED=0
