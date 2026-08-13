# Authority finding ownership

The repository is case-scoped: `AuthorityCaseFinding` is the only canonical external finding model/table. `AuthorityFinding` is absent. The row supports AuthorityCase, SubmissionCycle, source/evidence, category, authority status, timestamps, responses, and affected requirements. Permit and Submission consume this truth; no Permit-specific or Preparation-specific external-finding copy was introduced.

Engineering references the canonical row through `EngineeringAuthorityFindingLink.authority_finding_id`. Duplicate truth repaired: 0; new duplicate truth: 0.
