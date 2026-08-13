# Domain Reconciliation

The existing Party, Property, Proposal, Master Content, Document Version, Audit, RBAC, and Dashboard governance models remain canonical. The implementation adds shared regulatory, requirement, technical-rule, and form-runtime entities without duplicating those domains or changing Proposal-to-AuthorityCase behavior. A Proposal does not automatically create an AuthorityCase.

The four foundations are isolated behind `/api/regulatory`, `/api/requirements`, `/api/technical-rules`, and `/api/form-automation`.
