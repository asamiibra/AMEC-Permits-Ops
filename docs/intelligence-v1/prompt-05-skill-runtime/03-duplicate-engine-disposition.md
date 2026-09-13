# Duplicate-engine disposition

Executed source audit: one `SkillManifest` contract remains in `backend/app/services/intelligence_contracts.py`; one P05 `SkillRegistry` is in `backend/app/ai/skill_registry.py`; one P05 `ModelGateway` is in `backend/app/ai/gateway.py`; one generalized `SkillRuntime` is in `backend/app/ai/skill_runtime.py`; and the existing ledger/work-product/citation stores are reused. The old D3 orchestration is an explicitly bounded compatibility adapter and shares the gateway/provider boundary; P05 does not add a second retrieval or persistence store.
