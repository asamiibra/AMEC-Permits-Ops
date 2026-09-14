# P04 Context Compiler binding

Executed: `SkillRuntime` calls only `backend.app.services.context_compiler.compile_context` for generalized execution. It passes the server-resolved manifest and server actor identity, then verifies exact snapshot module/scope/project/skill/hash/schema/policy/context/auth identities and exact dependency identities, trust, and currentness before provider access. No `governed_retrieve` call or direct domain/master-content assembly exists in `skill_runtime.py`.
