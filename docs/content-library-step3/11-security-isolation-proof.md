# Security and isolation proof

- Proposal and resolver APIs apply role capabilities before returning consumer configuration.
- Engineering resolver access is denied to the BD persona before source enters its context.
- Form Automation now rejects a payload item different from the profile item and checks exact current reviewed source before instance creation/render.
- Completion checks case/project context and rejects profile/item/version mismatch.
- Preparation/submission tests retain case/project checks for transactional evidence.

Focused proof is in `backend/tests/test_content_library_step3_consumer_convergence.py`; no unauthorized master-content consumer result or cross-project leak was observed.
