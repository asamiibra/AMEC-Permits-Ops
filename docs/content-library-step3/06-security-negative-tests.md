# Security and negative coverage

Focused coverage exercises: zero candidates, multiple candidates, Needs Review, inactive, superseded/non-current, wrong module, wrong purpose, unauthorized resolver access, item/version mismatch, arbitrary source-version injection, and transactional/master separation.

Authorization is evaluated before a consumer receives resolved source context. Module binding does not substitute for capability; purpose does not substitute for applicability or readiness; a caller cannot force an arbitrary DocumentVersion into a FormInstance. Restricted/reference-only sources remain excluded from automated workflow use.

The retrieval service remains read-only and is not invoked as workflow selection authority. No AI selection or autonomous approval is added.
