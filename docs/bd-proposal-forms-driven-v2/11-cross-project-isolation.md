# Cross-project isolation

Status: `PROTECTED_AND_REGRESSION_VERIFIED`

All typed v2 companions carry a Proposal FK and every projection filters by the requested Proposal ID. Source links point to exact versions and are not globally searched by filename or hash alone. Client Party and Property links are explicit IDs; no name-only merge is performed. Accepted snapshots and Contract handoffs carry their originating Proposal/revision lineage.

The existing full backend suite and source-lineage cleanup regressions pass on PostgreSQL. No Proposal-owned Party, Property, ExternalBody, ServiceType, RequirementPolicy, or Form Automation master table was introduced.
