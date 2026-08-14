# Completion Case

Status: IMPLEMENTED_AND_VERIFIED.

`start_completion` explicitly creates/reuses a RegulatoryJourney, AuthorityCase, AuthorityCaseSubject, CompletionCaseLink, and scoped RegulatoryRelation records. Construction never auto-creates Completion; idempotency is keyed and concurrency-tested.
