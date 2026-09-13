# Prompt 03 existing seams and preservation map

This map was created after the exact Prompt 02 entry gate and before Prompt 03 source changes. The implementation extends the existing governed source/evidence seams and uses the Prompt 02 `CandidateAssertion` persistence contract as the only shared candidate object.

| Seam | Current behavior | P03 classification | Preservation rule |
| --- | --- | --- | --- |
| `backend/app/services/document_intelligence.py` — `RuleBasedDocumentClassifier` | deterministic Week 2 document classification | `REUSE_AS_IS` | Keep the rules-only classifier and its existing result shape; the new boundary only normalizes its result. |
| `backend/app/services/document_intelligence.py` — `LocalSyntheticExtractor` | deterministic synthetic field observations | `REUSE_AS_IS` | Keep extraction and `FieldObservation` ownership; normalize observations without treating them as verified truth. |
| `backend/app/services/document_intelligence.py` — new boundary adapter | no prior shared candidate adapter | `ADAPT_IN_PLACE` | Add a bounded `DocumentIntelligenceService` that delegates persistence to P02 contracts and owns only candidate/source normalization. |
| `backend/app/services/classifier_v2.py` — `classify_document` | deterministic rules-only Phase 5 classification envelope proposal | `WRAP` | Preserve the complete classification envelope and add a candidate projection alongside it. No LLM, learned lane, or projection activation. |
| `backend/app/services/bridge_intake.py` — `ingest_bridge_package` | validates allowlists, bounds, hash/signature, scope, replay; creates DocumentVersion, Phase4 evidence/classification, FieldObservation | `WRAP` | Run candidate normalization after the governed objects exist; preserve all controls, replay identity, and `verified_assertion_created=false` / `projection_created=false`. |
| `backend/app/services/phase4.py` | source/evidence/classification persistence, human review, promotion, typed projection | `LEGACY_COMPATIBILITY_ONLY` | Keep existing APIs and review behavior green. P03 never calls Phase4 review, promotion, or projection commands. |
| `backend/app/models/phase4_entities.py`, `backend/app/schemas/phase4.py` | accepted Phase4 source/evidence/classification/review/projection records | `REUSE_AS_IS` | Retain Phase4 envelopes as the historical evidence and review-compatible representation; CandidateAssertion is additive. |
| `backend/app/models/intelligence_entities.py` / `intelligence_contracts.py` | P02 shared candidate and deterministic identity contracts | `REUSE_AS_IS` | Use `create_candidate_assertion`, stable hashes, and P02 lifecycle states; do not add a second candidate table. |
| `backend/app/auth/bridge.py`, `backend/app/services/backend_realignment.py` | bridge identity validation and capability enforcement | `REUSE_AS_IS` | P03 adapters receive already-authorized identity/context and do not weaken or duplicate capability policy. |
| `backend/app/audit/service.py` | `AuditEvent` persistence | `REUSE_AS_IS` | Preserve existing audit calls; candidate normalization emits metadata-only audit details without source bytes/secrets. |
| existing `WorkflowTask` / `NotificationEvent` paths | legacy module review/work notification behavior | `PROHIBITED_TO_EXPAND` | Candidate creation does not create tasks, notifications, queues, or generic review authority. P07 owns rationalization. |
| Master Content and downstream currentness services | existing master-content dependency/currentness authority | `DEFER_TO_P07` | P03 binds source version identity it knows; generalized downstream invalidation remains later platform work. |

The canonical P03 boundary is therefore:

```text
governed source → existing DocumentVersion/evidence/observation/classification → shared CandidateAssertion → stop
```

No `VerifiedAssertion`, typed domain projection, central review record, model provider, retrieval system, or protected command is added by this map or its implementation.
