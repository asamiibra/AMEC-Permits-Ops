# Authorization and representation

`AuthorizationGrant` is a relational case record with grantor, grantee, authorization type, scope, effective dates, status, optional verified evidence `DocumentVersion`, and audit/lineage. `POWER_OF_ATTORNEY` is stored as a typed authorization, not as a filename-only assertion. Existing generic Representation/Authorization primitives remain reusable; Consent/NOC and an ExternalAgreement taxonomy are outside this upstream repair and are not invented here. Cross-project evidence is rejected.
