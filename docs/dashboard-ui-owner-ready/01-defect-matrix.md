# Dashboard v2 Owner UI defect matrix

| Area | Observed root cause | Closure fix | Evidence |
|---|---|---|---|
| Browser-controlled Forms | Real test writes were left active in the deployed DB | Conservative reconciliation archives confirmed probes only | `production-verification.json` |
| Deployment probe Forms | Deployment probe records were not archived after verification | Bootstrap reconciliation archives `DEPLOY-PROBE-*` | `production-verification.json` |
| Browser-controlled Engineering Works | Real browser rows polluted the Owner library | Archive by explicit probe text/ref patterns | `production-verification.json` |
| Browser-controlled Definitions | E2E terms were exposed as active business content | Archive confirmed browser-controlled terms | `production-verification.json` |
| Curated Forms missing | Owner data had no durable curated seed | Idempotent F-0001/F-0002 reconciliation | `dashboard-clean.png` |
| Curated Reports missing | Reports section was empty | Idempotent R-0001/R-0002 reconciliation | `reports.png` |
| Curated Engineering Works missing | Engineering section lacked usable examples | Idempotent E-0001/E-0002/E-0003 reconciliation | `engineering-works.png` |
| Curated Definitions missing | Definition records were absent/incomplete | Idempotent D-0001/D-0002 reconciliation | `definitions.png` |
| Raw category IDs | UI treated backend category identity as display text | Canonical category catalog drives labels and filters | `dashboard-clean.png` |
| Raw Used In enums | Module codes were rendered directly | Shared friendly labels and chips/picker | `dashboard-clean.png` |
| Raw statuses | `ACTIVE`, `CURRENT`, and `NO_VERSION` leaked to users | Friendly Current/Draft/Archived mapping | `dashboard-clean.png` |
| Raw version labels | `v—`/`NO_VERSION` were not actionable | Version N, Revision N, or No source file | `dashboard-clean.png` |
| Raw action verbs | Open/Modify/Version History were exposed | View/Edit/History actions | `dashboard-clean.png` |
| Inline editor failure | Editor behavior depended on an inline/legacy modal path | Responsive drawer editor with explicit states | `form-new.png`, `form-edit-metadata.png` |
| Footer submit failure | Drawer footer sat outside the form and did not submit | Drawer routes primary footer click to the active editor form | real-stack browser suite |
| Modify semantics | Metadata changes created document versions | Metadata PATCH updates the item in place and preserves version history | backend v2 tests |
| Source replacement semantics | Source replacement and metadata edit were not clearly separated | Optional replacement creates a new immutable version | real-stack browser suite |
| AI shell too large/raw | AI controls dominated the editor | Compact disabled AI Assist section with human-review copy | `form-new.png` |
| History unreadable | Raw history/status/download presentation | Dedicated history drawer with friendly version cards | `version-history.png` |
| Administration Forms drift | Admin Forms did not clearly share the canonical library | Shared `CanonicalFormsLibrary` component and real-stack parity test | `admin-forms.png` |

No frontend string filtering was used to hide records. Cleanup is backend reconciliation plus active/inactive query semantics.
