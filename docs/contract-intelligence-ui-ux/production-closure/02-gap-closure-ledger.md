# Gap-closure ledger

`CANDIDATE_SHA=c10e3aac0c47d9d158fffe65b89b5b3ce7fe1cc9`
`CANDIDATE_TREE=d0e4ad97b95fa85cfa7e8149c4640bc07f7f0051`
`MAIN_SHA=594b313a15cc6ade3f0505de395a5817c6337268`
`COMMAND=git diff; focused pytest; compileall`
`ENVIRONMENT=local synthetic test harness`
`DB_ENGINE=SQLite focused harness; prior clean PostgreSQL qualification is retained for the predecessor head`
`REAL_AMEC_DATA_USED=false`

| Gap | Candidate treatment | Result |
|---|---|---|
| Contract-derived Project start/advance gate | Revision-scoped, side-effect-free evaluator and activation mutation enforcement | Software-closed locally; payment-term scenarios still require target-DB proof |
| Design-entry dossier | Four canonical roles, exact current DocumentVersion lineage, Handover enforcement | Software-closed locally; focused mobilization test passes |
| Signed Proposal/PO/LPO acceptance | Existing Proposal response/verification/reconciliation records composed into a signed-commercial acceptance route | Software-closed by implementation; endpoint-specific tests still required |
| Date/duration semantics | Preserved as `OWNER_INPUT_REQUIRED` when no explicit duration-start fact exists | Owner decision remains open |
| Proactive operations exceptions | Existing missing-document work path retained | Full proactive evaluation not proven |
| Extension warning | Configurable policy projection added; default remains `OWNER_INPUT_REQUIRED` | Owner threshold/configuration remains open |
| Upload security | 25 MiB bound, filename/MIME/magic checks, production scanner fail-closed | Local code check passed; production scanner and storage qualification open |
| Migration history | Direct edits detected against main with no accepted rebaseline/forward fix | BLOCKED_GOVERNANCE_REBASELINE_REQUIRED |

No 309-row result was mass-flipped. The prior matrix remains the source of truth until atomic row-level re-adjudication is completed.
