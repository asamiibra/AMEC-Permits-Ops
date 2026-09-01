# Governed draft Apply contract

`POST /api/governed-prefill/preview` is read-only. It returns deterministic
field proposals, citations, source hashes, template pins, value-evidence
lineage, writer policy state, and a fingerprint over the material replay
inputs.

`POST /api/governed-prefill/apply` is an authenticated human/domain command.
It rebuilds the preview from current canonical state and fails closed unless
all pins, authority, purpose, case/project membership, current source and
mapping release, evidence, writer policy, preview fingerprint, expected draft
revision, and selected fields still match.

On success it mutates only an existing editable `DRAFT` FormInstance,
increments its draft revision once, persists field-level provenance/citations,
records the idempotency ledger, and writes an auditable event. It never writes
retrieval evidence, master content, source records, submissions, approvals,
signatures, invoices, construction authorization, handover, or closeout.

The template `DocumentVersion` and value evidence `DocumentVersion` /
`VerifiedAssertion` identities are stored separately and are reconstructable
for every applied field.
