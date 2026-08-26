# ProposalOps / AMEC — Repository Capture Update
**Update to:** `ProposalOps_AMEC_Repository_Master_Capture_and_Module_Validation_Index_2026-08-25.md`
**This update captured:** 2026-08-25, ~18:15 UTC (elapsed since base capture: roughly 5 hours)
**Branch count:** 61 → 69 (+8 new)

Diffed against the previous capture directly (`comm` on the branch-name lists, then `compare` API for ancestry) rather than re-deriving from scratch. No existing branch name moved — every update created a new branch, consistent with the no-force-push discipline observed throughout.

---

## Status of the four flagged cross-cutting items

### 1. Phase5 candidates A (r3r1) vs B (r3r2) — **resolved by continuation, not by explicit decision**

Two new branches, `phase5-classifier-shadow-validation-r3r1r1-v1` and `-r3r1r2-v1`, confirmed via `compare` to descend cleanly from **candidate A (r3r1)** — `ahead=1 behind=0` at each step. Candidate B (r3r2) is now `diverged ahead=2 behind=1` from the new tip: it was never merged, just left behind.

**So A won, in practice.** But there is still no record anywhere saying "B was evaluated and rejected because X" — it's an orphaned branch, not a formally superseded one. Worth a one-line closure note if this matters for audit purposes later; not urgent since the practical ambiguity is gone.

Substantive content added in r3r1→r3r1r2 (real work, not just evidence): modifications to `scripts/phase5/{evidence_validate,finalize,registry,sanitize_evidence,shadow_replay,source_preflight}.py` — the classifier evidence/finalization pipeline continuing to harden. No schema or infra changes.

### 2. Synology Preaccess vs T3 — **still unresolved, and the gap widened**

`synology-t3-owner-dsm-synthetic-r1r5-v1` vs `synology-preaccess-validation-r4-ci-v1`: **`diverged ahead=11 behind=1`** (was `ahead=5 behind=1` at last capture). T3 has continued independently; Preaccess has not been touched since `r4-ci` (04:13Z) while T3 advanced to `r1r5` (17:46Z) — 13+ hours of continued T3 work with no reconciliation.

**This is now the most concrete item to raise**, not because it's newly risky, but because the gap is growing rather than closing. If T3 is meant to supersede or absorb Preaccess's storage-layer work, that hasn't happened yet.

### 3. Azure SQL Foundation CI failure — **resolved**

`azure-sql-foundation-prephase5-r2r1-v1` now shows `"Azure SQL foundation static validation" = SUCCESS`. Worth noting the *mechanism*: `compare` shows `foundation-v1 → r2` and `r2 → r2r1` both as `diverged` (not clean fast-forward), and the file diff shows every file as "added" rather than "modified" — meaning each iteration is a **fresh rewrite of the same file set** from the Phase4 anchor, not an incremental patch on the previous attempt. That's a different work pattern than Phase5/T3 (which do show real incremental diffs) — not wrong, just worth knowing when you go read this branch, since `git log` on it won't show the evolution the commit messages describe ("decouple B1 quota," "repair R2 static ancestry check").

### 4. `backend/app/storage/smb.py` execution topology — **still not answered**

This was flagged as the single highest-priority item last capture: does this code run inside the Azure-hosted backend (a live architecture violation) or is it library code imported only by the NAS-hosted T3 execution surface (consistent with the locked design)?

One new, directly relevant artifact appeared: `scripts/synology_t3/host_bootstrap.py` (92 lines, new in T3 r1r4). This is exactly the kind of file that could resolve the question — it's plausibly the thing that imports `backend/app/storage/smb.py` on the NAS side. **Not yet confirmed either way** — I did not read its contents in this pass. This remains the top priority for the next check: open `host_bootstrap.py` and trace whether it imports from `backend.app.storage`, and separately confirm the Azure-side backend (`backend/app/api`, `backend/app/services`) does *not* import `backend/app/storage/smb.py` directly.

---

## Other confirmed-unchanged items (re-verified, not just assumed)

- **R13's own hardening CI check still fails** — now shown as `exact-head-hardening = failure` (the check name changed from "Azure A1 Batch 3A Step 4C Hardening," but the failing state is the same known role-provisioning defect, not a new problem).
- **R15 rebaseline remediation branch still does not exist.** The manifest/allowlist/readiness-check fixes from that prompt have not been executed against the live repo.
- **`main` unchanged**, still fully disconnected from all of this work (not re-verified with a fresh SHA diff this pass, but no new commits landed on it between captures per the branch list).

---

## Recommended next check, in order

```
1. Read scripts/synology_t3/host_bootstrap.py directly — this is the one file most
   likely to resolve item #4, which has been the top-priority open question across
   two capture passes now.
2. Confirm no Azure-side backend module imports backend/app/storage/smb.py directly.
3. If #1/#2 confirm NAS-only execution: close out item #4 as resolved-safe.
   If not: escalate immediately, this is an architecture violation in progress.
4. Decide whether synology-preaccess-validation-r4-ci-v1 is abandoned in favor of
   T3, or still needs to be reconciled into it — the gap is growing, not closing.
5. Everything else from the base capture's §5 validation order still applies.
```
