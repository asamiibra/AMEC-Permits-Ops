# Content Library Step 4 reconciliation matrix

Entry baseline: `534e525f4510b326ca2d2e85e3b41112a7b4c9c5`
Entry tree: `2a432bd1c2f638e4faab16eb2f1e4ce13d8538f8`

The candidate branches diverge from the accepted lineage at
`686ddbf79c25154e0c0d254912f66301af97b658`. They are read-only design and
test evidence. No branch is merged or rebased.

| Candidate | Surface | Classification | Reconciliation decision |
| --- | --- | --- | --- |
| `254c1dda` Owner correction | `frontend/src/Dashboard.tsx`, `MasterContentForms.tsx`, Owner E2E | `OWNER_PRODUCT_DECISION` / `PORTABLE_AND_VALID` | Carry the simple four-library Content Library surface, canonical master-library search, compact details, source/version history, and distinct Engineering Source Type / Discipline fields. |
| `254c1dda` Owner correction | retrieval, prefill, backend deletions and rewrites | `SUPERSEDED_BY_534` / `UNSAFE` | Do not import stale retrieval or remove accepted Step 3 services, tests, or evidence. |
| `ade765f5` draft/apply | `0059` migration and FormInstance apply fields | `PORTABLE_AND_VALID` | Reconcile as a minimal additive migration because durable draft revision, idempotency, provenance, and audit state cannot be represented safely by the `0058` schema. |
| `ade765f5` draft/apply | governed prefill apply service/API/tests | `PORTABLE_AND_VALID` with revalidation hardening | Rebuild against the accepted Step 3 retrieval and provenance contracts. Apply only to an existing DRAFT FormInstance through an authenticated domain command. |
| `ade765f5` draft/apply | dashboard, retrieval, consumer deletions | `SUPERSEDED_BY_534` / `UNSAFE` | Preserve accepted Owner-independent retrieval, consumer convergence, lineage, security, and evidence. |
| `90fa78f` commissioning prep | Step 4 plans, matrices, safety docs | `EVIDENCE_ONLY` / `TEST_ONLY` | Carry synthetic validation and safety boundaries only. Runtime commissioning remains pending the separate Azure workstream. |
| `90fa78f` commissioning prep | deployment, Azure, SQL, Synology, external runtime assumptions | `UNSAFE` | No deployment, mutation, commissioning, or external data access in this branch. |

Remote inventory at inspection time contains no newer Content Library branch
than the listed historical lanes and the accepted Step 3 reconciliation.

The implementation boundary is therefore:

```text
canonical library search ──> simple Owner Content Library UI
governed retrieval ──> prefill preview ──> human domain command ──> DRAFT only
```

Retrieval and preview remain read-only. The domain command owns the only
FormInstance write, with current-state revalidation, optimistic draft
concurrency, idempotency, field-level provenance, and audit evidence.
