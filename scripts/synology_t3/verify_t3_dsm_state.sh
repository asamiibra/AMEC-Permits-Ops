#!/usr/bin/env bash
set -euo pipefail
: "${1:?Usage: verify_t3_dsm_state.sh pre|post state.json}"
: "${2:?Usage: verify_t3_dsm_state.sh pre|post state.json}"
python3 - "$1" "$2" <<'PY'
import json, sys
from pathlib import Path

phase, path = sys.argv[1], Path(sys.argv[2])
payload = json.loads(path.read_text(encoding="utf-8"))
required = {"model", "dsm_version", "dsm_build", "hostname", "architecture", "active_lan_ip", "gateway", "docker_version", "test_share_exists", "accounts", "smb", "firewall", "auto_block", "tun1000", "test_share_permissions"}
missing = sorted(required - set(payload))
if missing:
    raise SystemExit("missing state fields: " + ",".join(missing))
if not isinstance(payload["active_lan_ip"], str) or ":" in payload["active_lan_ip"]:
    raise SystemExit("state must contain a sanitized IPv4 address")
if any(secret in json.dumps(payload).lower() for secret in ("password", "hash", "token", "private key")):
    raise SystemExit("state contains secret-like field")
if phase == "post" and payload.get("test_share_exists") is not True:
    raise SystemExit("synthetic test share must remain until independent acceptance")
print(json.dumps({"phase": phase, "status": "PASS"}, sort_keys=True))
PY
