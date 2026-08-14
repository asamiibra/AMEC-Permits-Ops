# Construction Domain Re-Certification

Construction remains bounded to post-approval execution controls. The PostgreSQL targeted suite passed 3 tests. It proves the human start gate, readiness blockers, work-control transition rejection, notification/correspondence behavior, both internal and authority inspection kinds, ConstructionIssue separation from AuthorityCaseFinding, and project-scoped isolation.

The authority-approved design snapshot and ConstructionDesignSnapshot remain immutable, exact-version pins. Start readiness is derived and returned `NOT_READY`; START without human authorization returns HTTP 409. STOP, POSTPONE, and RESUME are transition-controlled. Obligations, participants, authority notifications, correspondence, inspections, and issues remain distinct records with audit/lineage behavior. Completion context is read-only and deferred; no Completion or As-Built writes were added.
