# Future deployed-synthetic commissioning matrix

| Area | Checks |
| --- | --- |
| Runtime identity | exact revision, application SHA, frontend/backend provenance, environment, `synthetic_only`, migration head |
| Platform readiness | `/health/live`, `/health/ready`, DB connectivity, storage readiness, SQL dialect, no SQLite fallback |
| Authentication | authorized synthetic persona, role policy, no privilege widening |
| Content Library | Forms/Reports/Engineering Works/Definitions list/detail, Dashboard/Admin parity, current/needs-review/inactive, history |
| Retrieval | exact ID/reference, lexical, aliases, bilingual, current/history, citations, ambiguity/conflict, no fabricated result |
| Security | unauthorized caller, wrong project, restricted content, no unauthorized context/citation |
| Consumers | Proposal, Contract, Permit/Preparation, Engineering, Definitions, Dashboard cross-domain discovery |
| Non-mutation | retrieval leaves canonical counts unchanged; AI cannot execute protected actions |
| Data boundary | real AMEC reads/writes and Synology operations remain zero |

The deployed run must capture request/response evidence with fixture IDs,
canonical IDs, version IDs, citation IDs, access persona, and runtime release
provenance. It must not use production acceptance or protected human actions as
test substitutes.
