# Security and RBAC

Owner/System Admin roles control catalog creation, policy/rule approval, verified assertions, and mutable configuration. Responsible Engineer controls technical execution; Requirement Steward controls requirement approval. Business Development is denied from authority configuration and technical foundation writes in the E2E slice. All foundation writes and evaluations emit audit records with actor, correlation, entity, and before/after payloads.

No secrets, real PII, government data, portal credentials, or signature material were added.
