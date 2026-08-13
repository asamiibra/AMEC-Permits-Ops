# Security and isolation

Status: `PROTECTED_AND_REGRESSION_VERIFIED`

Existing persona capabilities were extended without adding visible roles. Engineering operations use project-scoped capability checks; populated project membership restricts Engineering actors to authorized project members. Cross-project revision, rendition, baseline, material, and member references are rejected by the backend.
