# ProposalOps SYN-T3 Owner DSM synthetic-share run

This handoff certifies only the read-only SMB source lane against one isolated synthetic DSM share. It does not authorize real AMEC data, business-share browsing, managed writes, parser/classifier execution, deployment, or production integration.

## Before execution

1. Confirm the independently accepted V2.3 application SHA is exactly `4925518b35b58956aaa5870f226af5e57d14b610` and the validation child is `cfa6a0271161f5131403c86aaaf728da8d21cc5f`.
2. Confirm the independent R1.1 handoff acceptance has passed. Do not execute DSM from the repair-build artifact alone.
3. In DSM, verify the current model, DSM build, architecture, active LAN IPv4, gateway, Docker version, SMB policy, firewall, Auto Block, `tun1000`, existing ProposalOps identities, and business-share ACL fingerprint. Record only sanitized values with `state_schema_version=SYN-T3-DSM-STATE-V1`, `phase=PRE` in `10_DSM_PRE_STATE.json`.
4. Confirm that `ProposalOps-T3-Synthetic`, `proposalops_t3_ro`, and `proposalops_t3_denied` do not already exist. If any name collides, stop; do not overwrite or reuse it.
5. Create the dedicated share and two non-admin local identities. Grant `proposalops_t3_ro` read-only access to this share only. Grant `proposalops_t3_denied` no access. Do not touch business shares or existing ProposalOps identities.
6. Run `seed_t3_synthetic_share.sh` in the isolated control directory and upload the complete generated `fixture_staging/cert/v1` directory as `cert/v1` under the dedicated share with DSM File Station.
7. Create `t3_ro.secret` and `t3_denied.secret` immediately before the run with mode `600`. Never place them in the handoff, image, evidence, logs, command line, or chat.

## One-time execution

Set `T3_NAS_IP` to the verified current NAS LAN IPv4 address, never a hostname or QuickConnect address. Set `T3_CONTROL_DIR`, `T3_EVIDENCE_DIR`, `T3_IMAGE_TAR`, and `T3_HANDOFF_DIR`, then run. The wrapper derives the authoritative image reference and harness SHA from `06_IMAGE_BUILD_POLICY.json`:

```sh
export T3_NAS_IP='<verified-lan-ip>'
export T3_CONTROL_DIR='/volume1/ProposalOps-T3-Control'
export T3_EVIDENCE_DIR="$T3_CONTROL_DIR/ProposalOps_SYN_T3_Return_<UTC_ID>"
export T3_IMAGE_TAR="$T3_CONTROL_DIR/proposalops-syn-t3-image.tar"
export T3_HANDOFF_DIR='/path/to/accepted/ProposalOps_SYN_T3_Handoff_<RUN_ID>'
./run_t3_owner_dsm.sh
```

The wrapper loads the immutable image, uses a read-only container filesystem, drops capabilities, mounts only the evidence directory writable, mounts both secrets read-only, and deletes the secret files on exit. It does not mount the DSM share, business data, Docker socket, or a host path containing the share.

## After execution

1. Capture sanitized `44_DSM_POST_STATE.json` with `state_schema_version=SYN-T3-DSM-STATE-V1`, `phase=POST`, all immutable PRE fields, `test_share_exists=true`, both T3 identities disabled, `t3_secret_files_retained=0`, `t3_recurring_tasks_enabled=0`, and `t3_task_removed=true`. The finalizer compares every immutable field; no field may be omitted.
2. Remove the one-time Task Scheduler entry. Disable both T3 identities. Keep the synthetic share and fixtures intact until independent acceptance.
3. Confirm both secret files are absent. Run `finalize_t3_return.py --return-root <return-root> --handoff-root <accepted-handoff-root>`, then run `validate_t3_return.py --return-root <return-root>`; it must PASS before downloading the archive.
4. Download the returned evidence archive through DSM File Station. Do not upload or share the secret files.

## Stop conditions

Stop and freeze evidence on any identity mismatch, collision, unexpected destination, SMB1/guest/anonymous session, unproven encryption or signing, successful RO mutation, denied-identity data access, root escape, secret match, real AMEC access, unauthorized DSM delta, or managed-write attempt. Do not repair the provider while connected to DSM.

Accepted residual deferrals remain `REAL_SMB_SERVER_SIDE_PAGINATION=NOT_VERIFIED`, `REAL_SMB_HARD_OPERATION_ABORT=NOT_VERIFIED`, and `REAL_DSM_REPARSE_REFERRAL=NOT_VERIFIED`.
