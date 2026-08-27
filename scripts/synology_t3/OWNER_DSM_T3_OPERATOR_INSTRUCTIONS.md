# ProposalOps SYN-T3 R1.6R2R1 Owner DSM synthetic-share run

This R1.6R2R1 handoff certifies only the read-only SMB source lane against one isolated synthetic DSM share. R1.6R1 remains historical independently accepted handoff evidence. R1.6R2 preserves its production PRE-bind repair and corrects only the T3 harness interpretation/evidence for smbprotocol 1.15.0 encrypted-session signing semantics: connection signing policy remains mandatory, encryption remains mandatory, and active encryption supplies session message integrity even when smbprotocol clears `session.signing_required`. R1.6R2R1 replaces the stale mutable validation contract, repairs the active handoff path, and preserves the mode-preserving extraction canary. It does not authorize real AMEC data, business-share browsing, managed writes, parser/classifier execution, deployment, or production integration. R1.6R2R1 build PASS and GitHub CI PASS do not authorize DSM.

The R1.5 run `SYN-T3-20260825T214812Z` is frozen historical failed evidence. It must not be reused, repaired, renamed, finalized as success, or mutated. The R1.6R1 handoff remains historical independently accepted evidence and is not to be changed. The live run `SYN-T3-20260827T002911Z` is frozen FAILED runtime evidence stopped at `security_all_signing_required`; physical DSM contact or SMB session creation may have occurred, but downstream T3 runtime acceptance did not complete. It must not be reused or converted to PASS. R1.6R2 repairs the harness only and requires fresh independent handoff acceptance; this candidate keeps `T3_OWNER_EXECUTION_READY=false`. No DSM rerun is authorized by this coding task. A future live DSM execution requires fresh explicit Owner authorization and a new run ID.

## Before execution

1. Confirm the independently accepted V2.3 application SHA is exactly `4925518b35b58956aaa5870f226af5e57d14b610` and the validation child is `cfa6a0271161f5131403c86aaaf728da8d21cc5f`.
2. Before any DSM execution, confirm that independent acceptance has passed for this exact R1.6R2R1 handoff candidate, binding the exact commit, tree, GitHub artifact ID and digest, handoff archive SHA256, image tar SHA256, image ID, application label, and harness label. A repair-build PASS or GitHub CI PASS by itself does not authorize DSM execution. `T3_OWNER_EXECUTION_READY` is set only by the independent acceptance record external to the handoff artifact, and this handoff candidate registry remains `T3_OWNER_EXECUTION_READY=false`.
3. Choose one exact run ID: `RUN_ID=SYN-T3-<UTC_TIMESTAMP_OR_OWNER_RUN_ID>`. The same value must bind `T3_CONTROL_DIR`, wrapper `T3_RUN_ID`, the missing-share name, and the evidence directory. Never use an implicit second ID.
4. Before creating any T3 DSM object, verify the current model, DSM build, architecture, active LAN IPv4, gateway, Docker version, SMB policy, firewall, Auto Block, `tun1000`, existing ProposalOps identities, and business-share ACL fingerprint. Record only sanitized values with `state_schema_version=SYN-T3-DSM-STATE-V1`, `phase=PRE` at `$T3_CONTROL_DIR/10_DSM_PRE_STATE.json`.
5. Confirm that `ProposalOps-T3-Synthetic`, `proposalops_t3_ro`, and `proposalops_t3_denied` do not already exist. If any name collides, stop; do not overwrite or reuse it.
6. Use DSM File Station to copy/upload the exact accepted `fixture_staging/cert/v1` tree into `ProposalOps-T3-Synthetic/cert/v1`. Do not generate a new fixture corpus on DSM. Run `seed_t3_synthetic_share.sh` only as its read-only shipped-fixture verifier.
7. Use the accepted control root `/volume1/ProposalOps-Inventory/SYN-T3/$RUN_ID`. The handoff build identity and live run identity are separate authorities: `T3_HANDOFF_BUILD_ID=SYN-T3-R1R6R2R1-<GITHUB_RUN_ID>` identifies the accepted GitHub artifact, while `T3_RUN_ID=SYN-T3-<FRESH_UTC_TIMESTAMP_OR_OWNER_RUN_ID>` identifies this live run. Run all host Python with `-B`; export `PYTHONDONTWRITEBYTECODE=1`. If any `.pyc` or `__pycache__` exists in the extracted handoff, discard and re-extract the exact accepted artifact; stop without deleting contamination.
8. First pass the host UID/GID collision gate. Numeric secret/evidence ownership is `10001:10001` only after that gate: secrets are regular non-symlink files mode `0600`, evidence is mode `0700`, and cleanup removes both ephemeral secrets on every exit path.
9. Canonical PRE remains `$T3_CONTROL_DIR/10_DSM_PRE_STATE.json`, owned by `root:root` with mode `0600`. Never chmod or chown it to satisfy Docker. The R1.6R1 wrapper creates exactly one ephemeral byte-identical runtime PRE at `$T3_CONTROL_DIR/.runtime-pre-$T3_RUN_ID/10_DSM_PRE_STATE.json`, owned by `10001:10001` with mode `0400`, binds only that runtime copy, and deletes it on every exit path. A pre-existing runtime directory is a fail-closed collision.

10. R1.6R2 security evidence is written to `20_SMB_SESSION_SECURITY.json` immediately after `security_introspection()` and before any hard security check. The evidence distinguishes `connection_require_signing`, `session_require_encryption`, `session_encrypt_data`, `session_signing_required`, and derived `session_integrity_protected`/`integrity_mode`. Active encrypted sessions may report `session_signing_required=false`, but `connection_require_signing=true`, `session_require_encryption=true`, and `session_encrypt_data=true` remain mandatory.

## Provenance and extraction authority

- R1.6R1 is the historical independently accepted handoff; its later live execution stopped at the obsolete `security_all_signing_required` predicate.
- The frozen live run `SYN-T3-20260827T002911Z` is FAILED/FROZEN and is not reusable or convertible to PASS.
- R1.6R2 commit `daf85ec3e2b8623e6f8d900276b508ba2dcdfa09` correctly repaired the security root cause and passed strong local validation, but CI run `33030368693` failed at the stale mutable Phase5 wildcard gate; no R1.6R2 handoff artifact was produced and it was not independently accepted or authorized for DSM.
- R1.6R2R1 preserves the R1.6R2 security logic byte-for-byte, replaces the stale wildcard validation with exact immutable accepted lineage, repairs the current handoff path, and hardens mode-preserving extraction. It remains a candidate until independent handoff acceptance.

The GitHub artifact ZIP is only a transport envelope. Verify its accepted artifact ID and digest first, then extract the inner `ProposalOps_SYN_T3_Handoff_SYN-T3-R1R6R2R1-<GITHUB_RUN_ID>.tar.gz` with a mode-preserving tar operation. Do not trust a reconstructed handoff directory produced by a ZIP extraction method that discards Unix modes. Validate the extracted handoff, run immutable preflight, verify `13_FIXTURE_MANIFEST.json` is mode `0644` and non-root readable, and run the `UID/GID 10001` plus `--network=none` manifest-read canary before PRE/live execution.

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
export T3_HANDOFF_BUILD_ID='SYN-T3-R1R6R2R1-<GITHUB_RUN_ID>'
export T3_HANDOFF_DIR='/path/to/accepted/ProposalOps_SYN_T3_Handoff_'"$T3_HANDOFF_BUILD_ID"
export T3_IMAGE_TAR="$T3_HANDOFF_DIR/proposalops-syn-t3-image.tar"
export T3_EVIDENCE_DIR="$T3_CONTROL_DIR/ProposalOps_SYN_T3_Return_$T3_RUN_ID"
export PYTHONDONTWRITEBYTECODE=1
unset T3_BOOTSTRAP_ONLY
test -z "${T3_BOOTSTRAP_ONLY+x}"
export T3_NAS_IP='<verified-lan-ip>'
./run_t3_owner_dsm.sh
```

`T3_HANDOFF_BUILD_ID` binds the accepted GitHub artifact, handoff directory, and image/harness identity. `T3_RUN_ID` binds `T3_CONTROL_DIR`, the wrapper run ID, the missing-share run suffix, and the runtime evidence directory. They must remain distinct.

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
