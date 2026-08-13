# Gap reconciliation matrix

| Gap | Repository finding | Surgical resolution | Evidence |
|---|---|---|---|
| Full PostgreSQL proof | Entry was 0048; final proof absent | Fresh 0049 PostgreSQL database and full suite | `20-postgresql-full-suite.md` |
| Finding ownership | Only `AuthorityCaseFinding` exists | No duplicate truth added; Engineering remains a link | `06-authority-finding-ownership.md` |
| External agreement | No `ExternalAgreement` table | Typed `agreement_type` guard on Contract/Revision | `08-external-agreement-guard.md` |
| Optional Project | Billing context already allowed nullable project in policy seam | Snapshot and explicit project/issue policies added | `09-optional-project-billing.md` |
| Issue vs delivery | Issue event did not prove receipt | Delivery and acknowledgment event tables/endpoints added | `12-invoice-issue-delivery-model.md` |
| Event due date | Due basis was not event-aware | Typed basis, pending state, deterministic derivation | `14-due-date-basis.md` |
| Frontend | Project UUID was labelled as Project Code | Activated Project Code is shown only from canonical project; otherwise context | `24-frontend-build.md` |
| Test isolation | PostgreSQL FK cleanup exposed ordering defects | Corrected only test teardown ordering | Full PostgreSQL run |
