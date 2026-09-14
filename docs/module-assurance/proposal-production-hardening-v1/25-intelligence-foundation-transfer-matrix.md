# P1–P8 Intelligence foundation transfer matrix

P07 was used as the reusable shared-foundation reference. P08 was used only as
an implementation reference. The Intelligence branch was not whole-merged.

| Capability | Source occurrence | Transfer result | Evidence |
|---|---|---|---|
| Shared contracts / AIWorkProduct / ContextSnapshot / ContextDependency | `f8d10e73c563563f7ede24dd9d775b7bdbdf85f` | TRANSFERRED | `backend/app/services/intelligence_contracts.py`, shared Intelligence models and migration |
| Document Intelligence | `b6d5a18d495982e56f2cc1effe76ea7aa83caa7c` | TRANSFERRED | `backend/app/services/document_intelligence.py` and platformization tests |
| Governed Context Compiler | `fb5702f97daa2d1c6f5cc875b7aca0ab76d4f25d` | TRANSFERRED | `backend/app/services/context_compiler.py` and scope/currentness tests |
| Model Gateway / provider boundary | `1b991857f6fca5ec52822eb2b63c962ae3fb62c3` | TRANSFERRED | `backend/app/ai/gateway.py`, provider and runtime tests |
| Reservation/idempotency/currentness fence | `1b551cd71a98186d8e289a8dff7f97dcdeadd2f0`, `f37fa2aa54393aa0e52d351c1ffbe1b8350dc3f4`, `8fcfa3b41cff1058addeb9fa0d1bd763f8315bcd`, `b21ab2fe5e30e306a9bc40149ba10324f0bebd9b` | TRANSFERRED | P07 control-plane tests and final one-head graph |
| Structured output / citation validation | `1b991857f6fca5ec52822eb2b63c962ae3fb62c3` | REUSED_AND_EXTENDED | strict schemas now back six precise Proposal skills |
| Tool registry/runtime | P07/P05 source line | REUSED | Proposal V1 manifests allow zero tools; arbitrary tool execution is unavailable |
| Evaluation / observability | P07/P05 source line | REUSED | shared eval-pack and runtime observability seams; final exact acceptance remains open |
| Human review / VerifiedAssertion boundary | P07 source line | REUSED | module-owned Proposal review binding and shared promotion path |
| Proposal Intelligence V1 module implementation | `a054db7e5e10137593f73380509e97ac0817c44f` | SELECTIVELY ADAPTED | six-skill registry/purposes replaced the four-skill pilot |
| P08 evidence/UI-only history | `dabde93131f725a0db588b4cc6583e778a5a6c97` | NOT_WHOLE_MERGED | historical provenance only |

## Required six-skill result

```text
PROPOSAL_AI_SKILL_COUNT=6
proposal.tender-intake-analysis=1.0.0
proposal.requirement-evidence-analysis=1.0.0
proposal.section-draft=1.0.0
proposal.commercial-consistency-review=1.0.0
proposal.lpo-variance-analysis=1.0.0
proposal.handoff-preflight=1.0.0
OWNING_MODULE=BD_PROPOSAL
CANONICAL_WRITE_AUTHORITY=NONE
PROTECTED_ACTION_AUTHORITY=NONE
REGISTERED_TOOL_COUNT=0
```

Each manifest has one precise purpose, strict `additionalProperties=false`
output schema, governed evidence trust floor, interactive-only V1 support,
dependency capture, invalidation declaration, model-policy binding, context
budget, and cost/token budget. The Proposal workspace exposes the six bounded
experiences directly; no generic chat or central AI review queue was added.
