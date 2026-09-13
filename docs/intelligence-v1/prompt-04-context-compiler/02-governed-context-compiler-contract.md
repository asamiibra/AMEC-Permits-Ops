# Governed Context Compiler contract

`backend/app/services/context_compiler.py` provides `ContextCompileRequest`, `ContextSourceSpec`, `CompiledContextItem`, `CompiledContext`, and the internal `GovernedContextCompiler` service (aliased as `ContextCompiler`).

The request accepts only correlation, actor identity, business scope, schema/policy versions, a validated P02 `SkillManifest`, and typed source specifications. Pydantic `extra="forbid"` rejects caller-supplied persona, capabilities, authorization hash, synthetic flags, context hashes, SQL, model/table names, arbitrary payloads, raw content, and import paths.

The result contains the server-derived actor persona and authorization hash, exact manifest identity, deterministic context hash, minimized item projections, deterministic optional omissions, aggregate classification/sensitivity, and the persisted snapshot identity. Complete ORM objects, source text, source bytes, prompts, tokens, and model output are never persisted.

Trust ordering is `CANDIDATE=10`, `GOVERNED_EVIDENCE=20`, `VERIFIED=30`, `CANONICAL=40`. A source must be both explicitly allowed by `SkillManifest.allowed_context_types` and at or above `input_trust_floor`.

The service has no canonical-write, protected-action, review, workflow, model, retrieval, vector, embedding, or external HTTP authority.
