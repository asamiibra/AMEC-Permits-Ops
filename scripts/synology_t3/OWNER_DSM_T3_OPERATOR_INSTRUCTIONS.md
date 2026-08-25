# ProposalOps SYN-T3 Owner DSM synthetic-share run

This handoff certifies only the read-only SMB source lane against one isolated synthetic DSM share. It does not authorize real AMEC data, business-share browsing, managed writes, parser/classifier execution, deployment, or production integration.

## Before execution

1. Confirm the independently accepted V2.3 application SHA is exactly `4925518b35b58956aaa5870f226af5e57d14b610` and the validation child is `cfa6a0271161f5131403c86aaaf728da8d21cc5f`.
2. In DSM, verify the current model, DSM build, architecture, active LAN IPv4, gateway, Docker version, SMB policy, firewall, Auto Block, `tun1000`, and existing ProposalOps identities. Record only sanitized values in `10_DSM_PRE_STATE.json`.
3. Confirm that `ProposalOps-T3-Synthetic`, `proposalops_t3_ro`, and `proposalops_t3_denied` do not already exist. If any name collides, stop; do not overwrite or reuse it.
4. Create the dedicated share and two non-admin local identities. Grant `proposalops_t3_ro` read-only access to this share only. Grant `proposalops_t3_denied` no access. Do not touch business shares or existing ProposalOps identities.
5. Run `seed_t3_synthetic_share.sh` in the isolated control directory and upload only its generated `cert/v1` tree to the dedicated share with DSM File Station.
6. Create `t3_ro.secret` and `t3_denied.secret` immediately before the run with mode `600`. Never place them in the handoff, image, evidence, logs, command line, or chat.

## One-time execution

Set `T3_NAS_IP` to the verified current NAS LAN IPv4 address, never a hostname or QuickConnect address. Set `T3_CONTROL_DIR`, `T3_EVIDENCE_DIR`, `T3_IMAGE_TAR`, and `T3_IMAGE_REF`, then run:

```sh
export T3_NAS_IP='<verified-lan-ip>'
export T3_CONTROL_DIR='/volume1/ProposalOps-T3-Control'
export T3_EVIDENCE_DIR="$T3_CONTROL_DIR/ProposalOps_SYN_T3_Return_<UTC_ID>"
export T3_IMAGE_TAR="$T3_CONTROL_DIR/proposalops-syn-t3-image.tar"
export T3_IMAGE_REF='proposalops/syn-t3:4925518'
./run_t3_owner_dsm.sh
```

The wrapper loads the immutable image, uses a read-only container filesystem, drops capabilities, mounts only the evidence directory writable, mounts both secrets read-only, and deletes the secret files on exit. It does not mount the DSM share, business data, Docker socket, or a host path containing the share.

## After execution

1. Capture sanitized `90_DSM_POST_STATE.json` and compare it with the pre-state. Verify global SMB, firewall, network, `tun1000`, business shares, and existing ProposalOps identities are unchanged.
2. Remove the one-time Task Scheduler entry. Disable both T3 identities. Keep the synthetic share and fixtures intact until independent acceptance.
3. Confirm both secret files are absent. Run `validate_t3_return.py --return-root <return-root>`; it must PASS before downloading the archive.
4. Download the returned evidence archive through DSM File Station. Do not upload or share the secret files.

## Stop conditions

Stop and freeze evidence on any identity mismatch, collision, unexpected destination, SMB1/guest/anonymous session, unproven encryption or signing, successful RO mutation, denied-identity data access, root escape, secret match, real AMEC access, unauthorized DSM delta, or managed-write attempt. Do not repair the provider while connected to DSM.

Accepted residual deferrals remain `REAL_SMB_SERVER_SIDE_PAGINATION=NOT_VERIFIED`, `REAL_SMB_HARD_OPERATION_ABORT=NOT_VERIFIED`, and `REAL_DSM_REPARSE_REFERRAL=NOT_VERIFIED`.
