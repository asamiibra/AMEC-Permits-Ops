# Authority-negative matrix

| Attempt | Result |
| --- | --- |
| Candidate created as `PROMOTED` without explicit verified-assertion reference | rejected: `INTELLIGENCE_PROMOTION_REQUIRES_EXPLICIT_REFERENCE` |
| Skill manifest declares `CANONICAL`, `PROTECTED`, `ACCEPTED`, or `AUTHORIZED` authority | rejected: `INTELLIGENCE_CANONICAL_WRITE_AUTHORITY_FORBIDDEN` |
| Work product output class is `APPROVED` | rejected: `INTELLIGENCE_OUTPUT_CLASS_UNSUPPORTED` |
| Work product payload carries top-level protected side-effect field | rejected: `INTELLIGENCE_PROTECTED_SIDE_EFFECT_FORBIDDEN` |
| Dependency metadata contains raw/text/bytes/content/prompt/output key | rejected: `INTELLIGENCE_DEPENDENCY_RAW_CONTENT_FORBIDDEN` |
| Candidate or work product persistence | records an envelope only; no module transition, review queue, or protected command is called |

`VerifiedAssertion`, existing module review commands, `AuditEvent`, and `MasterContentDependency` remain the authority seams. Prompt 02 introduces no central review queue, no automatic invalidation command, and no autonomous approval/protected action.
