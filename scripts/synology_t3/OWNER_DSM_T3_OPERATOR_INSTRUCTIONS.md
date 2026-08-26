# ProposalOps SYN-T3 R1.6 Owner DSM synthetic-share run

This R1.6 handoff certifies only the read-only SMB source lane against one isolated synthetic DSM share. R1.6 exists solely to close the root-controlled PRE bind permission defect; it does not authorize real AMEC data, business-share browsing, managed writes, parser/classifier execution, deployment, or production integration. R1.6 build PASS and GitHub CI PASS do not authorize DSM.

The R1.5 run `SYN-T3-20260825T214812Z` is frozen historical failed evidence. It must not be reused, repaired, renamed, finalized as success, or mutated. Another real DSM attempt requires a new run ID, which must not be created in this task. Independent R1.6 handoff acceptance must occur first; this candidate keeps `T3_OWNER_EXECUTION_READY=false`. A future live DSM execution requires fresh explicit Owner authorization.

## Before execution

1. Confirm the independently accepted V2.3 application SHA is exactly `4925518b35b58956aaa5870f226af5e57d14b610` and the validation child is `cfa6a0271161f5131403c86aaaf728da8d21cc5f`.
2. Before any DSM execution, confirm that independent acceptance has passed for this exact R1.6 handoff candidate, binding the exact commit, tree, GitHub artifact ID and digest, handoff archive SHA256, image tar SHA256, image ID, application label, and harness label. A repair-build PASS or GitHub CI PASS by itself does not authorize DSM execution. `T3_OWNER_EXECUTION_READY` is set only by the independent acceptance record external to the handoff artifact, and this handoff candidate registry remains `T3_OWNER_EXECUTION_READY=false`.
3. Choose one exact run ID: `RUN_ID=SYN-T3-<UTC_TIMESTAMP_OR_OWNER_RUN_ID>`. The same value must bind `T3_CONTROL_DIR`, wrapper `T3_RUN_ID`, the missing-share name, and the evidence directory. Never use an implicit second ID.
4. Before creating any T3 DSM object, verify the current model, DSM build, architecture, active LAN IPv4, gateway, Docker version, SMB policy, firewall, Auto Block, `tun1000`, existing ProposalOps identities, and business-share ACL fingerprint. Record only sanitized values with `state_schema_version=SYN-T3-DSM-STATE-V1`, `phase=PRE` at `$T3_CONTROL_DIR/10_DSM_PRE_STATE.json`.
5. Confirm that `ProposalOps-T3-Synthetic`, `proposalops_t3_ro`, and `proposalops_t3_denied` do not already exist. If any name collides, stop; do not overwrite or reuse it.
6. Use DSM File Station to copy/upload the exact accepted `fixture_staging/cert/v1` tree into `ProposalOps-T3-Synthetic/cert/v1`. Do not generate a new fixture corpus on DSM. Run `seed_t3_synthetic_share.sh` only as its read-only shipped-fixture verifier.
7. Use the accepted control root `/volume1/ProposalOps-Inventory/SYN-T3/$RUN_ID`. Run all host Python with `-B`; export `PYTHONDONTWRITEBYTECODE=1`. If any `.pyc` or `__pycache__` exists in the extracted handoff, discard and re-extract the exact accepted artifact; stop without deleting contamination.
8. First pass the host UID/GID collision gate. Numeric secret/evidence ownership is `10001:10001` only after that gate: secrets are regular non-symlink files mode `0600`, evidence is mode `0700`, and cleanup removes both ephemeral secrets on every exit path.
9. Canonical PRE remains `$T3_CONTROL_DIR/10_DSM_PRE_STATE.json`, owned by `root:root` with mode `0600`. Never chmod or chown it to satisfy Docker. The R1.6 wrapper creates exactly one ephemeral byte-identical runtime PRE at `$T3_CONTROL_DIR/.runtime-pre-$T3_RUN_ID/10_DSM_PRE_STATE.json`, owned by `10001:10001` with mode `0400`, binds only that runtime copy, and deletes it on every exit path. A pre-existing runtime directory is a fail-closed collision.

## One-time execution

After independent acceptance, and only during the later separately authorized DSM execution, create the fresh run directory as root. The control root must already exist and not be a symlink; the `SYN-T3` parent may be created under it. The run directory must not already exist. If it exists, stop with `STOP_T3_RUN_ID_OR_CONTROL_DIR_COLLISION`; never reuse it.

```sh
export T3_CONTROL_ROOT='/volume1/ProposalOps-Inventory'
export T3_RUN_ID='SYN-T3-<UTC_TIMESTAMP_OR_OWNER_RUN_ID>'
export T3_CONTROL_DIR="$T3_CONTROL_ROOT/SYN-T3/$T3_RUN_ID"
sudo mkdir -p "$T3_CONTROL_ROOT/SYN-T3"
test ! -e "$T3_CONTROL_DIR"
sudo mkdir "$T3_CONTROL_DIR"
sudo chown 0:0 "$T3_CONTROL_DIR"
sudo chmod 700 "$T3_CONTROL_DIR"
export T3_HANDOFF_DIR='/path/to/accepted/ProposalOps_SYN_T3_R1R6_Handoff_<RUN_ID>'
export T3_IMAGE_TAR="$T3_HANDOFF_DIR/proposalops-syn-t3-image.tar"
export T3_EVIDENCE_DIR="$T3_CONTROL_DIR/ProposalOps_SYN_T3_Return_$T3_RUN_ID"
export PYTHONDONTWRITEBYTECODE=1
unset T3_BOOTSTRAP_ONLY
test -z "${T3_BOOTSTRAP_ONLY+x}"
export T3_NAS_IP='<verified-lan-ip>'
./run_t3_owner_dsm.sh
```

Before creating the T3 share or accounts, validate PRE with the shipped helper:

```sh
PYTHONDONTWRITEBYTECODE=1 bash "$T3_HANDOFF_DIR/verify_t3_dsm_state.sh" pre "$T3_CONTROL_DIR/10_DSM_PRE_STATE.json"
```

Only after PRE PASS may the Owner create the synthetic share and accounts. Then manually place exactly `$T3_CONTROL_DIR/t3_ro.secret` and `$T3_CONTROL_DIR/t3_denied.secret`; each contains only its corresponding account password plus an optional final newline. They must be regular non-symlink non-empty files, are never printed/hashed/committed/uploaded, and must never be supplied through an environment variable or command-line argument. The wrapper performs the authoritative collision gate, numeric chown, and mode `0600`.

The wrapper creates/prepares the evidence directory, loads the immutable image, uses a read-only container filesystem, drops capabilities, mounts only the evidence directory writable, mounts the ephemeral runtime PRE read-only, mounts both secrets read-only, and deletes the secrets and runtime PRE on exit. It does not mount the canonical root:root PRE, the DSM share, business data, Docker socket, or a host path containing the share.

## After execution

1. Capture sanitized `44_DSM_POST_STATE.json` with `state_schema_version=SYN-T3-DSM-STATE-V1`, `phase=POST`, all immutable PRE fields, `test_share_exists=true`, both T3 identities disabled, `t3_secret_files_retained=0`, `t3_recurring_tasks_enabled=0`, and `t3_task_removed=true`. The finalizer compares every immutable field; no field may be omitted.
2. Validate POST before finalization: `PYTHONDONTWRITEBYTECODE=1 bash "$T3_HANDOFF_DIR/verify_t3_dsm_state.sh" post "$T3_CONTROL_DIR/44_DSM_POST_STATE.json"`.
3. Remove the one-time Task Scheduler entry. Disable both T3 identities. Keep the synthetic T3 share and fixtures intact until independent acceptance.
4. Confirm both secret files are absent. Run `python3 -B finalize_t3_return.py --return-root <return-root> --handoff-root <accepted-handoff-root>`, then run `python3 -B validate_t3_return.py --return-root <return-root>`; it must PASS before downloading the archive.
5. Download the returned evidence archive through DSM File Station. Do not upload or share the secret files.

## Stop conditions

Stop and freeze evidence on any identity mismatch, collision, unexpected destination, SMB1/guest/anonymous session, unproven encryption or signing, successful RO mutation, denied-identity data access, root escape, secret match, real AMEC access, unauthorized DSM delta, or managed-write attempt. Do not repair the provider while connected to DSM.

Accepted residual deferrals remain `REAL_SMB_SERVER_SIDE_PAGINATION=NOT_VERIFIED`, `REAL_SMB_HARD_OPERATION_ABORT=NOT_VERIFIED`, and `REAL_DSM_REPARSE_REFERRAL=NOT_VERIFIED`.
