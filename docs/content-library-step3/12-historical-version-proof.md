# Historical version proof

Proposal acceptance and Contract snapshot patterns store exact source version and hash. Form instances and generated artifacts store exact source DocumentVersion and mark source drift for revalidation. Project evidence and submission artifacts already retain exact transactional DocumentVersion pointers. Definition history retains immutable revisions while `current_revision_id` advances.

Required outcome: later V2 selection never rewrites a completed/accepted V1 artifact. Historical binding rewrite count is zero.
