# Contract UI action and API coverage

This is the aggregate companion to the atomic Owner matrix. It records the
current Contract controls that are visible in the workspace and the evidence
chain required for a consequential action.

| UI control | Component | Read path | Write/action path | Authority | Persistence | Test | Result |
|---|---|---|---|---|---|---|---|
| Edit prospective Contract revision | `ContractRevisionEditor` | `GET /api/admin/contracts/{id}` | `PATCH /api/admin/contracts/{id}` | `CONTRACT_EDIT` | `ContractRevision` + history readback | `test_admin_contract_owner_session.py` | PASS |
| Store Client Document / PO / LPO | `ContractSourceIntake` | Contract document projection | multipart `POST .../documents/upload` | `CONTRACT_EDIT` | `DocumentVersion` bytes/hash + evidence | binary/source tests + browser | PASS |
| Record terms, deliverables, client inputs | `ContractCommitments` | current revision projection | `POST .../commercial-terms`, `.../deliverables`, `.../client-inputs` | `CONTRACT_EDIT` | revision-bound commitment rows | Contract owner tests | PASS |
| Review and accept | `Review` | readiness/current revision | `POST .../checker`, `.../authority`, `.../accept` | distinct checker/review/accept capabilities | `ContractRevision` + acceptance snapshot | negative/API tests + browser | PASS |
| Record execution, client delivery, Operations handoff | `ContractExecutionHandoff` | evidence milestone projection | exact evidence/handoff routes | execution/handoff capabilities | append-only `ContractAdminEvidence` | ordering tests + browser | PASS |
| Project Activation | `Mobilization` | canonical readiness projection | `POST .../activate-project` | `PROJECT_ACTIVATE` | `ProjectActivation` + `Project` | activation tests | PASS |
| Create ServiceEngagement | `ServiceScopeSetup` / Handover | downstream context | owning Handover endpoint | `SERVICE_SCOPE_CREATE` | Handover ServiceEngagement | Handover bridge tests | CROSS_MODULE_PASS |
| Contact routing / missing-document follow-up | Operations panels | contact/readiness projection | purpose-specific routing and follow-up endpoints | `CONTRACT_EDIT` | contact evidence / WorkflowTask | operational contact tests | PASS |
| Extension request / authority decision | extension panels | operations extension history | `POST .../extension-requests`, `.../extension-decisions` | edit vs review authority | append-only evidence; original dates unchanged | API + browser | PASS |
| Open Finance/Billing | Operations | billing context | navigation/deep link only | no Contract mutation | Billing owns invoices/payments | billing boundary tests | CROSS_MODULE_PASS |
| Contract Intelligence catalogue | `ContractIntelligence` | `GET .../intelligence` | no execution endpoint | `CONTRACT_READ` only | no AIWorkProduct persistence | catalogue tests + browser | PASS |

No Intelligence card is clickable and no current UI control claims to run a
skill, show findings, or show citations from a nonexistent AIWorkProduct.
