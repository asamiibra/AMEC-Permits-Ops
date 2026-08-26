# ProposalOps / AMEC — Repository Master Capture & Module Validation Index

**Captured:** 2026-08-25, ~13:00 UTC, via GitHub API against `asamiibra/AMEC-Permits-Ops`
**Purpose:** one indexed, evidence-grounded snapshot of everything currently live in the repository, organized so each module/phase can be validated independently against a fixed baseline.

---

## 0. Read this first — the repo is moving faster than any capture can keep up with

During this single capture session, the branch count went **18 → 55 → 61**. The newest commit landed roughly 20 minutes before the final query. Timestamps show commits arriving minutes apart, continuously, across parallel workstreams.

**Consequence: treat every SHA in this document as a citation, not a live pointer.** Before validating any module, re-resolve its branch name to a current SHA and diff against the SHA recorded here — if they differ, the module has moved and this capture's findings may no longer apply to its current state (though they remain valid history for the SHA cited).

This document captures a **coherent snapshot**, verified by direct `git`/`gh api` inspection — SHAs, tree contents, ancestry (`compare` API `ahead_by`/`behind_by`/`merge_base`), and CI conclusions were all read directly, not inferred from branch names or commit messages.

---

## 1. Verified lineage map

```
main (3474b35, 2026-08-21)                          [SEPARATE LINEAGE — R13 NOT an ancestor]
 └── historical branch/*, fix/vercel-* (2026-08-15/16, pre-dates this saga)

phase3b-canonical-safety (cc5aa76, 2026-08-18)
        │
        ▼
azure-a1-f1 → -batch3a → -step3 → -step4 → -step4c   = R13
  (23d0674)    (77f4baa)  (021b900) (446dfe5) (96c4b90, 2026-08-22T20:31)
  R13's OWN CI CHECK STILL FAILS (role-provision defect, tracked, unresolved)
        │
        ▼
proposalops-db-rebaseline-r13-0059 (8dfcc55, 2026-08-23T14:03)
  35 commits ahead of R13
        │
        ▼
phase3c-module-truth-v1 (44968e3, 2026-08-23T16:50)
  4 commits ahead of rebaseline
        │
        ├──────────────────────────────────────────────┐
        ▼                                               │
phase4-v36r1-azure-sql-port-v1 (53bae9f)                │
        │  ~24 iteration branches, closure/validation   │
        │  ping-pong, spanning 2026-08-24T00:41→21:18   │
        ▼                                               │
phase4-v36r1-final-closure-r3r5r3-v1 (707003fc, 20:00)  │
  ★ CONFIRMED STABLE APPLICATION-CONTENT ANCHOR ★       │
  (validated: everything after this in the Phase4       │
   family only touches .github/workflows/*.yml —        │
   zero app-code delta)                                 │
        │                                                │
        ├─────────────────┬─────────────────┐            │
        ▼                 ▼                 ▼            │
  Phase5 family      Azure SQL         Synology          │
  (below)            Foundation        preaccess ─────────┘  (branches directly
                      (below)          (below)                off phase3c, 15
                                                               commits, parallel
                                                               to Phase4 entirely)
```

**Phase5 family** (branches from `707003fc`, diverges internally — see §3.5):
```
phase5-classifier-shadow-validation-v1 (2026-08-25T00:08)
  → -ci-v1 → -r3-v1 → -ci-r3-v1 → -r3r2-v1 (11:35)
                                 ↘
                                  r3r1-v1 (12:42)  ← DIVERGED from r3r2, not descended from it
                                  → -ci-r3r1-v1 (12:44)
```

**Synology Preaccess family** (branches from `707003fc`, linear):
```
synology-preaccess-validation-v1 (02:25) → r2 → r2-ci → r3 → r3-ci → r4 → r4-ci (04:13)
```

**Synology T3 family** (branches from `707003fc`, linear internally, but **diverged from preaccess-r4-ci**):
```
synology-t3-owner-dsm-synthetic-v1 (04:42) → r1 → r1r1 → r1r2 → r1r3 (12:53, latest commit in whole repo)
```

**Azure SQL Foundation** (branches directly from `707003fc`, single commit so far):
```
azure-sql-foundation-prephase5-v1 (cb2cfab, 12:37)
  ★ CURRENTLY FAILING its own "Azure SQL foundation static validation" CI check ★
```

---

## 2. Pre-existing product base — carried unchanged under everything above

Every tip inspected carries the same ~470 files of the original ProposalOps product, untouched by any AMEC/Azure-migration branch:

```
~172  frontend/*
 ~92  backend/tests/* (general, non-Phase5/Synology)
 ~54  backend/app/* (core, non-Phase4)
 ~39  backend/app/services/*
 ~37  backend/app/api/*
 ~35  backend/app/models/*
```

Plus a large body (~3,300+ files) of historical development artifacts: `artifacts/*` (ui-conformance, universal-design-audit, final-platform-closure, dashboard-e2e, and ~30 more closure/reconciliation directories) and `docs/*` (week-3 through week-14, billing-invoice, completion-asbuilt, handover-admin-closeout, permit-authority-case-ux, etc.) — the original weeks-1-through-14 ProposalOps build history this project's memory already documents. **Not in scope for this capture** — nothing in the current AMEC/Azure work touches it, and it isn't part of "one by one validate each module" for the corpus/migration workstream.

One notable pre-existing item: `backend/mock-systems/` and `mock-systems/synology` (~158 files) — the **synthetic** Synology adapter (`MockBinaryStore`) that predates all of this. Distinct from the **real** Synology work in §3.6/3.7 below — worth not conflating the two.

---

## 3. Module-by-module validation index — the AMEC/Azure migration work

### 3.1 — DB Migration Rebaseline
```
Branch:  proposalops-db-rebaseline-r13-0059
Tip SHA: 8dfcc55a48f44ba88ee5cb9fb9c0c7dd096f42dd  (2026-08-23T14:03:50Z)
CI:      "ProposalOps database rebaseline validation" = SUCCESS
```
**Already independently audited this session** (145+55 checks). Confirmed: 59 legacy migrations correctly archived byte-identical, single active baseline `baseline_r13_0059` with zero forbidden patterns, downgrade fail-closed. **Three specified gates not satisfied as specified**: archive manifest.json missing, allowlist exceeded by 4 paths (2 legitimately needed for a fix, 1 runtime file with a deleted safety check, 1 test file), 12 files still reference the legacy head outside the allowlist. A remediation prompt (R15) was written and independently validated (77 checks) — **not yet confirmed executed against the live branch.**
**Validate next:** re-check whether R15's remediation branch (`proposalops-r15-remediation`) exists on the remote; if not, it hasn't run yet.

### 3.2 — Phase3C Canonical Module Truth
```
Branch:  phase3c-module-truth-v1
Tip SHA: 44968e3d43571ceb1df8493da683ff9e51a146d9  (2026-08-23T16:50:07Z)
CI:      storage-contract = SUCCESS (no dedicated Phase3C workflow observed in this capture)
```
Content confirmed: 13 contracts + 10 docs under `contracts/amec/phase3c/` and `docs/amec/phase3c/`, including `AMEC_MODULE_TRUTH_CONTRACT_v1.json` (686KB), Owner Decision Ledger, Freeze Manifest, Classifier Handoff, Deferred Deployment Readiness record, plus supplementary validation artifacts (`GOVERNANCE_VALIDATION`, `REFERENCE_INTEGRITY`, `V6B_SUPPLEMENTARY_SEMANTIC_VALIDATION`) not present when this was first reviewed — **these are new since the earlier audit and haven't been checked.**
**Validate next:** whether the 2026-08-22 Owner decisions (RBAC matrix, Project Code format, Handover process, archive rule) and the 49 pre-existing `artifacts/*/owner-decision-*.json` records were actually consumed and reconciled, per the B2 finding from the earlier R15 audit — not yet confirmed either way against this specific content.

### 3.3 — Phase4 Database Engine Port (PostgreSQL → Azure SQL)
```
Branch:  phase4-v36r1-final-closure-r3r5r3-v1  (the confirmed stable content anchor)
Tip SHA: 707003fc16767fb28b9c968fbcf168ab03ebadc1  (2026-08-24T20:00:26Z)
CI:      storage-contract = SUCCESS
```
Already independently reviewed this session (Azure SQL Database vs. Managed Instance decision) and reviewed again as the runbook's accepted anchor. Confirmed: active migration is `baseline_phase4_v36_azure_sql.py`, `mssql+pyodbc` scheme with `Encrypt=yes`/`TrustServerCertificate=no` enforced, 20 Phase4 contracts, dedicated `scripts/db_azure_sql/*` gate tooling. **~24 subsequent iteration branches exist past this point but confirmed to touch only `.github/workflows/*.yml`** — no re-audit needed for those; this SHA remains the real target.
**Open, unresolved:** the ODBC container build/install step was failing in CI as of the last check on this family (`msodbcsql18` proof). Re-verify current status against `phase4-v36r1-final-validation-r3r5r3-e2-v1`'s workflow run before assuming it's fixed.

### 3.4 — Azure SQL Foundation (infrastructure-as-code)
```
Branch:  azure-sql-foundation-prephase5-v1
Tip SHA: cb2cfab23774cf13ea52a4eb8ce1be408f973913  (2026-08-25T12:37:16Z)
CI:      "Azure SQL foundation static validation" = FAILURE  ← ACTIVE, UNRESOLVED
```
**Brand new — first appearance of this branch was during this capture session.** Content: `infra/azure_sql_foundation/main.bicep` + separate modules for `budget.bicep`, `core.bicep`, `network.bicep`, `private_dns.bicep`, plus a `foundation.bicepparam.example` and a validation script. The separate `network.bicep`/`private_dns.bicep` split is a good sign — suggests the subnet-delegation-conflict finding from the runbook review (Private Endpoints cannot share a subnet delegated to another Azure service) may have been designed around correctly. **Unverified — the branch's own CI is currently red.**
**Validate next, highest priority in this family:** read the actual failure output of "Azure SQL foundation static validation" before anything else in this branch is trusted. This is the branch most directly answering the runbook gaps I flagged (PostgreSQL-era Bicep, subnet delegation, `WEBSITE_VNET_ROUTE_ALL`/`WEBSITE_DNS_SERVER` for private DNS) — worth checking specifically whether those two App Service settings appear anywhere in `core.bicep`, since their absence was the concrete Stage A9 failure I predicted last review.

### 3.5 — Phase5 Classifier Shadow Validation — **two unreconciled candidates**
```
Candidate A: phase5-classifier-shadow-validation-r3r1-v1
             19a938761d9465d7fd2e0f61656f3d4838153d74  (2026-08-25T12:42:49Z)
Candidate B: phase5-classifier-shadow-validation-r3r2-v1
             9b57f0dd4937790b3a737357e72407b4afef8c73  (2026-08-25T11:35:55Z)
CI:      storage-contract only observed for both; no dedicated Phase5 workflow
         conclusion captured in this pass — recheck directly.
```
**Confirmed via `compare` API: A and B diverged from a common `r3` ancestor — neither descends from the other** (each is exactly 1 ahead / 1 behind the other). **Confirmed via file-list diff: both touch the identical 17 files** (`test_phase5_evidence_integrity.py`, `test_phase5_finalizer_negative.py`, the classifier robustness corpus, freeze manifest, and all of `scripts/phase5/*`). This means A and B are two independently-written, mutually exclusive implementations of the same fix — **not a sequence, not additive.** One of them needs to be selected as canonical, or the actual difference between them needs to be understood as a real design choice, before either can be treated as "the" Phase5 state.
**Validate next, before anything else in Phase5:** diff A against B directly (not each against r3) to see what they actually disagree about. Whichever isn't selected should be explicitly marked superseded/abandoned rather than left ambiguous.

### 3.6 — Synology Preaccess (storage layer)
```
Branch:  synology-preaccess-validation-r4-ci-v1
Tip SHA: cfa6a0271161f5131403c86aaaf728da8d21cc5f  (2026-08-25T04:13:22Z)
CI:      "Synology preaccess validation R4" = SUCCESS
```
**Touches live production code, not just new scaffolding**: `backend/app/storage/{smb.py,external.py,factory.py,port.py,__init__.py}` — the actual `BinaryStorePort`/`SMBBinaryStore` abstraction this project's storage architecture is built on. Confirmed by direct read: `external.py` implements bounded reads (`SourceReadBudgets`: max file bytes, max total bytes/run, max files/run, max runtime seconds), a `StabilityState` machine, and `SourceChangedDuringImport` mutation detection — this is consistent in shape with the read-only, budgeted, change-detection discipline this whole project has converged on for source access.
**Not yet confirmed, and this is the single highest-priority item in this entire capture:** *where does this code execute?* If it runs as part of the live Azure-hosted backend, that's Azure establishing direct SMB reachability to the Synology NAS — which every architecture decision in this project, repeatedly and explicitly, has forbidden (`DIRECT_SYNOLOGY_FROM_AZURE=false`, `AZURE_SOURCE_ACCESS_MODE=OUTBOUND_EVIDENCE_ONLY`). If it's shared library code imported only by the NAS-hosted execution surface (see §3.7), it's consistent with the locked architecture. **Do not proceed past this item without resolving it.**

### 3.7 — Synology T3 Owner DSM Synthetic (NAS execution host)
```
Branch:  synology-t3-owner-dsm-synthetic-r1r3-v1
Tip SHA: aa6b7e16595bf31a533427e99a1131337a7d7c59  (2026-08-25T12:53:56Z — latest commit in the repo)
CI:      "Synology T3 synthetic DSM handoff build R1.3" = SUCCESS
```
**This appears to be the live implementation of the "NAS itself is the execution host" architecture locked earlier in this project** — the Docker-on-DS220+ decision, closed after the VPN/Tailscale/VMM loop. Content: `scripts/synology_t3/Dockerfile`, `run_t3_owner_dsm.sh`, `seed_t3_synthetic_share.sh`, `t3_runner.py`, `network_guard.py`, `preflight_t3_handoff.py`, plus an `OWNER_DSM_T3_OPERATOR_INSTRUCTIONS.md` and `OWNER_DSM_T3_ATTESTATION_TEMPLATE.json` — matching the operator-mediated access model (Owner runs it via DSM, Codex authors it) established for that exact reason.
**Confirmed diverged from Synology Preaccess (§3.6) at their common base** — the two have NOT been reconciled with each other yet, despite both being Synology-facing work from the same day.
**Validate next:** whether `network_guard.py` actually enforces `--network none` for the parser stage, whether the Fetcher/Parser/Uploader credential separation from the locked architecture decision is present, and whether `t3_runner.py` is the thing that imports `backend/app/storage/smb.py` from §3.6 — which would resolve the open question in 3.6 in the *safe* direction (SMB code runs on the NAS, not in Azure).

---

## 4. Cross-cutting findings — resolve these before deep module-by-module validation

Ranked by how much they block everything downstream:

1. **`backend/app/storage/smb.py` execution topology (§3.6) — unresolved, architecture-critical.** This is not a style question; if the answer is wrong, it's a live violation of a repeatedly-reaffirmed boundary. Resolve first.
2. **Synology Preaccess and Synology T3 have diverged and need reconciliation** — same day, same subject, not merged into each other.
3. **Phase5 candidates A (r3r1) and B (r3r2) are mutually exclusive** — pick one or understand the real disagreement before treating Phase5 as "done."
4. **Azure SQL Foundation is currently failing its own CI** — the branch most directly relevant to the last runbook review, unverified.
5. **R13's own hardening check still fails** (role-provisioning defect) — known, tracked since the first audit pass, still unresolved at the anchor commit everything else descends from. Doesn't block downstream work (it's been correctly treated as historical), but worth remembering it's still an open item, not solved by anything downstream.
6. **`main` remains completely disconnected** from all of this — confirmed again this pass. Nothing here is deployable from `main` today.

---

## 5. Recommended validation order

```
1. Resolve §3.6 topology question (blocks trusting Synology work at all)
2. Reconcile §3.6 vs §3.7 (Preaccess vs T3)
3. Read the Azure SQL Foundation CI failure (§3.4) — small branch, fast to diagnose
4. Diff Phase5 candidates A vs B directly (§3.5) — pick or reconcile
5. Confirm whether R15 rebaseline remediation actually ran (§3.1)
6. Re-audit Phase3C's new supplementary contracts against 2026-08-22 Owner decisions (§3.2)
7. Recheck Phase4's ODBC/msodbcsql18 CI status (§3.3) — likely still open
```

---

## 6. Evidence

Raw API responses, trees, and comparisons backing every claim in this document are cached at:
```
/private/tmp/claude-501/.../scratchpad/data2/
  branches.json, branch_dates_sorted.tsv
  tree_<branch>.json  (9 full recursive trees)
  runs_p1-p4.json      (400 most recent workflow runs)
  tip_ci_status.txt
```
This is session-scoped scratch space, not durable — re-run the capture rather than relying on it existing later.
