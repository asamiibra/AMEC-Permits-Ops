# ProposalOps Intelligence v1 — Locked Architecture Contract

STATUS=CANONICAL_TARGET_DESIGN
VERSION=1
CHANGE_AUTHORITY=EXPLICIT_OWNER_DESIGN_AMENDMENT_REQUIRED

This document is the canonical target design for ProposalOps Intelligence v1. It is an architecture contract only; it introduces no runtime, schema, deployment, or data change.

## 1. One shared Intelligence Platform

ProposalOps has one shared Intelligence Platform. No AI infrastructure stack is created per module.

Shared platform responsibilities are:

- Document Intelligence
- Governed Context Compiler
- Skill Registry
- Model Gateway
- Tool Runtime
- Structured Output Runtime
- citation/provenance
- AIWorkProduct ledger
- evaluation
- observability
- dependency/invalidation infrastructure

## 2. Document Intelligence

Document Intelligence owns source intake, stability/currentness, immutable DocumentVersion/hash/provenance, extraction, classification, relationship candidates, requirement candidates, contradiction/change detection, and confidence/provenance.

It outputs:

```text
Evidence
CandidateAssertion
CandidateRelationship
MachineProcessingState
```

It does not own business approval, professional approval, commercial approval, module work queues, module human review, final external release, or protected business decisions.

## 3. Governed Context Plane

The Context Compiler assembles authorized/current context from canonical SQL truth, VerifiedAssertions, governed evidence, approved/current Master Content, persona/project/authority scope, and module-owned business context.

It fails closed on stale sources, superseded versions, ambiguous canonical sources, missing required sources, unauthorized sources, cross-project leakage, and unresolved currentness.

## 4. Shared Business Intelligence Runtime

The shared runtime executes module-owned skills. Allowed AI output classes are:

```text
CANDIDATE
ANALYSIS
DRAFT
RECOMMENDATION
```

The defaults are:

```text
canonical_write_authority=NONE
protected_action_authority=NONE
```

A skill may suggest a reviewer or next action. A skill does not make the human decision.

## 5. Module-owned skills

Every business skill has an owning module. A future `SkillManifest` includes at minimum:

```text
skill_id
skill_version
owning_module

input_schema
output_schema

allowed_context
input_trust_floor

allowed_tools
model_policy

output_class

review_trigger_policy
suggested_review_role

dependency_capture_policy
invalidation_policy

evaluation_pack

canonical_write_authority
protected_action_authority
```

## 6. Human review lives inside the module

Human review is not a Document Intelligence layer and is not a Business Intelligence layer. Each consuming module owns whether review is required, review-work-item creation, its module queue, priority, SLA, reviewer persona, reviewer capability, the evidence/context shown to the reviewer, Accept / Correct / Reject / Defer / Escalate semantics, the resulting domain transition, protected-action eligibility, and decision audit.

Shared review UI components are allowed. Shared immutable evidence/decision primitives are allowed. A central business review queue and a central AI review authority are prohibited.

## 7. VerifiedAssertion boundary

`VerifiedAssertion` may be a shared reusable platform object, but its business verification authority originates from the authorized module human decision.

Canonical flow:

```text
CandidateAssertion
→ Module Work Item
→ Authorized Human Review
→ Module Command
→ VerifiedAssertion
```

Cross-module consumption is allowed only under explicit trust/currentness policy. Reuse of a verified fact does not transfer the originating reviewer's protected authority.

## 8. Protected actions

AI may not autonomously accept a proposal, accept a contract, activate a project, professionally approve, sign professional/regulatory undertakings, approve commercial variations, authorize final external submission, issue or verify payment, perform protected construction-start, approve an as-built baseline, or execute closeout protected actions.

Protected actions remain domain commands gated by authorized humans.

## 9. Master Content and invalidation

Master Content owns approved/current source state, source version/hash, governance/applicability, dependency truth, and change detection. Shared dependency infrastructure may detect affected downstream artifacts. The owning module determines the operational response and owns any human revalidation work item.

## 10. Durable AI work products

Future durable `AIWorkProduct` objects capture exact dependency identity sufficient to determine whether an output remains current. At minimum:

```text
work_product_id
skill_id
skill_version
owning_module

DocumentVersion IDs + hashes

VerifiedAssertion IDs + versions

canonical SQL entity/revision/state identities

Master Content revision identities

policy/ruleset versions

context_hash

model/runtime identity

structured output

citations

created_at

CURRENT | STALE | INVALID

stale_reason
superseding_dependency
```

## 11. Operational model

There is no separate “AI operating system.” Users continue to work inside:

```text
Proposal / BD
Contract
Engineering / Permit
Billing
Completion / Handover
Owner decision workflows
```

AI enriches those workflows. AI does not create a second organizational queue structure.

## 12. Canonical architecture sentence

> ProposalOps shall implement one shared governed Intelligence Platform. Document Intelligence produces provenance-preserving evidence and candidates; the Context Compiler assembles authorized current business context; module-owned skills use the shared reasoning runtime to produce analyses, drafts, recommendations and candidates. Human review, business decisions, state transitions and protected authority remain embedded in the consuming module. Shared intelligence may prepare work; it never becomes the business authority.
