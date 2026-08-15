# Purpose bindings and resolvers

BD consumes backend-controlled resolver results. The live singleton purposes are `PROPOSAL_TEMPLATE` and `PROPOSAL_CHECKLIST` on module `BD`; Administration consumes `CONTRACT_TEMPLATE`. Engineering preparation resolves current eligible Engineering Works through the shared canonical tables and defers that view before preparation.

Resolver selection uses canonical identity, active module binding, current version metadata, and governance readiness. Ambiguous singleton configuration is surfaced as `CONFIGURATION_CONFLICT`; there is no name-based or latest-created fallback.
