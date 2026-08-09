# Primary ASSISTED operator runbook

Evidence class: synthetic implementation evidence. Roles are enforced by existing Week 1–12 RBAC and human gates. Every consequential action stops on mismatch, preserves evidence, and escalates rather than guessing.

| # | Operator action / actual route | Expected state and evidence | Failure / do not do / fallback / escalation |
|---:|---|---|---|
| 1 | Open project: `GET /api/projects` | Canonical project ID | Wrong project: stop; do not relink; Process Champion |
| 2 | Verify application: `GET /api/applications` | Request number, municipality, permit type match | Identity mismatch: stop and preserve correlation |
| 3 | Inspect Synology link: `GET /api/projects/{id}` | SYNOLOGY link visible | Missing link: L1 case; do not create guessed path |
| 4 | Inspect Excel link | Workbook/sheet/row link visible | Locked/missing workbook: support case; do not overwrite |
| 5 | Ingest/register documents: `GET /api/projects/{id}/documents` | DocumentVersion registered | Unreadable document: manual/keyed fallback and evidence |
| 6 | Review extraction/observations | Raw evidence and candidate values visible | Low-confidence value: human verification required |
| 7 | Verify critical facts: `POST /api/observations/{id}/verify` | VerifiedAssertion current | Wrong/conflicting fact: Finding/conflict; never silently select |
| 8 | Resolve conflicts: Week 2 conflict APIs | Conflict resolved by allowed role | Critical conflict: block package |
| 9 | Check owners/property/representation | Shares, authorization, validity pass | Missing/expired representation: block and escalate |
| 10 | Evaluate requirements: `POST /api/projects/{id}/readiness/evaluate` | Requirement result hash recorded | Expired NOC/credential: block; Requirement Steward/Engineer |
| 11 | Render forms: `/api/projects/{id}/forms/{code}/render` | Versioned form output | Mapping gap: stop and configuration review |
| 12 | Update Excel projection | Controlled projection, human region protected | Workbook lock: retry after owner confirmation; no force overwrite |
| 13 | Review drawing metadata | Project/plot/revision controls pass | Mismatch: Responsible Engineer Finding |
| 14 | Evaluate package readiness | READY or explicit blockers | Missing evidence: no approval bypass |
| 15 | Internal technical review | Responsible Engineer evidence | Professional decision cannot be delegated to support/model |
| 16 | Package approval | Requirement Steward/approved role | Stale package: regenerate; never reuse prior approval |
| 17 | Create PreparationRevision | Exact package/hash binding | Stale package/revision: block |
| 18 | Start assisted municipality preparation | Current revision only | Wrong revision: stop and rebaseline |
| 19 | Enter fields/dropdowns | Target rendering rules and identity match | Portal mismatch: exception and reread |
| 20 | Enter grids | Canonical row/business keys | Grid mismatch: STOP; no row-position guessing |
| 21 | Associate attachments | Locked category/hash/language manifest | Wrong category/missing file: STOP and manual replacement |
| 22 | Save/reopen | Persistence evidence and readback match | Silent mismatch is prohibited; reconcile |
| 23 | Reconcile portal state | `PortalReconciliationResult=PASS` | Mismatch: invalidate affected revision/package |
| 24 | Capture precheck | Current `AuthorityPrecheckRun` | Unavailable: manual fallback and support escalation |
| 25 | Resolve precheck Finding | Finding→Task→Notification and evidence | Blocking Finding: remains blocking |
| 26 | Handoff | `/api/submission-handoffs`, exact revision/package | Final Submitter independently reviews; acceptance is not submit |
| 27 | Confirm human submission | Human evidence / SubmittedSnapshot | No reference/state match: do not record confirmed |
| 28 | Monitor | `/api/monitoring/run-due-synthetic` or manual capture | Auth/MFA/outage: bounded retry or manual fallback |
| 29 | Triage status/comment | NO_CHANGE or AuthorityEvent | Repeated comment dedupes; drift pauses parser |
| 30 | Correct Finding | `/api/findings/{id}/resolutions` | Evidence policy and verifier enforced |
| 31 | Verify closure | `/api/finding-resolutions/{id}/verify` | Rejected closure remains open/reopened |
| 32 | Resubmission readiness | Week 10 readiness route + preventive context | Open blocker/stale input: block; Process Champion/Engineer |

Portal drift sequence: `DRIFT → stop trusting parse → preserve raw evidence → manual capture → maintainer escalation → contract validation → re-enable`. Support follows L1→L2→L3; professional decisions remain with the Responsible Engineer.
