# ProposalOps AI-D0/D1 architecture freeze

## Frozen base and scope

- Source base SHA: `787a6b0f67975af500e09cc833910f1cea6c0f07`
- Source base tree: `11c3f55a64510a85b083359ef467ff4efed643b1`
- Architecture contract: `AI-D0-D1-ARCHITECTURE-1.0`
- Context manifest contract: `AI-CONTEXT-MANIFEST-1.0`
- Initial purpose policy: `ENGINEERING_TECHNICAL_DRAFT`, policy version `ENGINEERING_TECHNICAL_DRAFT-1.0`

This tranche freezes architecture and implements an authorization/context
seam only.  It has no model invocation, provider SDK, task enqueue, worker,
AI ledger, migration, canonical write, protected action, Azure mutation,
Synology access, SMB access, or real AMEC content path.

## D0 decisions

The only execution modes are `INTERACTIVE` and `BACKGROUND`.  `AUTO`,
`HYBRID`, implicit defaults to background, router selection, and hidden
interactive-to-background fallback are prohibited.

Interactive semantics are: authenticated full principal, AI authorization,
exact target/context resolution, bounded database read, future provider call,
and future non-authoritative response validation.  The database session and
any transaction are released before a future provider call.  A future
interactive failure is a typed failure; it is never silently enqueued.

Background semantics are a future explicit durable task: commit, worker claim,
future provider invocation, validation, and result persistence.  D0/D1 does
not create or enqueue that task.

The pinned hosted-model architecture is:

| Field | Frozen value |
| --- | --- |
| provider | `AZURE_OPENAI_FOUNDRY` |
| model | `gpt-5.1` |
| model version | `2025-11-13` |
| deployment type | `Standard` |
| resource region | `uaenorth` |
| processing boundary | `UAE_NORTH_REGIONAL` |
| model router | disabled |
| fallback models | zero |
| provider-managed memory | disabled |
| provider-managed threads | disabled |
| real content | disabled |
| external invocation | disabled |
| canonical writes | `ZERO` |
| protected actions | `ZERO` |

This is a **PINNED MODEL ARCHITECTURE**, not deployed-model acceptance.
`MODEL_DEPLOYED`, runtime proof, inference proof, quota, networking,
managed identity, and production readiness remain unproven and are outside
this tranche.  The hosted model is not a global ProposalOps readiness
dependency: ProposalOps may be healthy while AI assist is degraded.

Existing governed retrieval remains the only canonical AI content source.
There is no second RAG store, vector database, Azure AI Search integration,
agent framework, provider memory, or provider thread state.  Governed
prefill remains deterministic, model-free, citation-preserving,
preview-first, human-applied, DRAFT-only, version-pinned, and unchanged.

## D1 authorization policy

The AI policy is separate from the legacy retrieval purpose matrix.  D1 does
not add generic `AI_CONTEXT` to that matrix.  The caller must explicitly
request the enum-backed `ENGINEERING_TECHNICAL_DRAFT` purpose.

Its allowed roles are `OWNER_SPONSOR`, `SYSTEM_ADMIN`, and
`RESPONSIBLE_ENGINEER`; its required ProposalOps capability is
`ENGINEERING_PROJECT_READ`; its target entity types are `PROJECT` and
`AUTHORITY_CASE`; and its execution modes are `INTERACTIVE` and `BACKGROUND`.
Master content, transactional evidence, and definitions may be read only
through the existing governed retrieval restrictions.  Only sensitivity
`NONE`, current transactional evidence, and non-superseded content are
accepted.  Real content, canonical writes, and protected actions are zero.

The route depends on the existing full `AuthenticatedPrincipal`, not on a
role-only dependency.  Client fields cannot supply user ID, role, office,
Entra identity, capabilities, actor, membership, sensitivity override, or
real-data/authority flags.  Owner and system-admin requests require an
explicit target project/entity.  A responsible engineer requires an exact
active `EngineeringProjectMember` where:

```text
EngineeringProjectMember.project_id == resolved_project_id
EngineeringProjectMember.actor_id == AuthenticatedPrincipal.user_id
EngineeringProjectMember.status == ACTIVE
```

`role.value`, `X-Dev-Actor`, payload actors, assigned-engineer text, office
co-membership, email, display name, UPN, client project lists, and frontend
visibility are not project authority.  The known D1 limitation is that
non-owner project context fails closed when exact canonical membership is not
provable.

For `AUTHORITY_CASE`, the server resolves the case and requires
`subject_type == PROJECT` with `subject_id` equal to the resolved canonical
Project row.  The client cannot claim an entity/project relationship.

The environment gate requires `synthetic_only == true` and
`real_data_allowed == false`.  Otherwise the context route returns
`AI_REAL_CONTENT_NOT_AUTHORIZED`.

## Provider-safe context manifest

`POST /api/ai/context/manifest` authenticates the full principal, authorizes
the purpose and exact scope, applies the synthetic boundary, invokes
`governed_retrieve()` using an internally server-bound `READ` access context,
and returns a deterministic provider-safe manifest.  It performs zero
persistent writes, provider calls, and background enqueues.

The manifest contains the frozen contract/architecture/policy versions,
purpose, execution mode, exact project/entity scope, policy decision and
capability, governed retrieval contract version, and explicitly whitelisted
retrieval items/citations.  Relationship context is allowlisted; arbitrary
ORM or envelope dictionaries are never serialized.  Every item is tagged
`UNTRUSTED_EVIDENCE_TEXT`.

Retrieved source content is DATA, not system instruction.  It cannot redefine
AI policy, grant capabilities, authorize tool use, authorize protected action,
or request additional data access.  This boundary is frozen for D2/D3.

The deterministic budget is 20 items, 16 KiB UTF-8 per item, and 96 KiB UTF-8
total.  Items are never silently truncated or discarded.  Over-budget input
returns `AI_CONTEXT_BUDGET_EXCEEDED`.

The manifest fingerprint is SHA-256 over sorted-key, stable-separator,
UTF-8 canonical JSON with deterministic item/citation ordering.  It includes
architecture/policy versions, purpose, mode, scope, canonical identities,
exact document versions, source hashes, states, safe content, and citations;
volatile timestamps, correlation IDs, bearer tokens, and session IDs are not
included.

## Hard boundaries and future tranches

The D1 context manifest is **not authority to send real AMEC content to a
model**.  Real content egress remains disabled and the external invocation
count is zero.  The existing retrieval API remains deterministic and
external-model-free; `/api/retrieval/answer` is not repurposed.

AI-D2 is not authorized.  AI-D3 is not authorized.  This freeze does not
prove model deployment, runtime, inference quality, quota, networking,
managed identity, production AI readiness, real-data AI readiness, Synology
AI readiness, or protected-human AI authority.
