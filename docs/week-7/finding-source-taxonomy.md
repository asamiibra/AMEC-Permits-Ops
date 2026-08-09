# Finding Source Taxonomy

`FindingSourceType` is controlled and persisted on both `AuthorityEvent` and `Finding`:

- `INTERNAL_PREFLIGHT`
- `PORTAL_VALIDATION`
- `AUTHORITY_PRECHECK`
- `OFFICIAL_MUNICIPALITY_COMMENT`
- `EMAIL_NOTICE`
- `MANUAL_OPERATOR_CAPTURE`

`AUTHORITY_PRECHECK` is pre-submission and must retain an `AuthorityPrecheckRun` and `PreparationRevision`. `OFFICIAL_MUNICIPALITY_COMMENT` is post-submission/manual synthetic review and must retain a `SubmissionCycle`; it must not be converted into a precheck result.
