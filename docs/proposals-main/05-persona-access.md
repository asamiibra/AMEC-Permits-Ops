# Persona access

| Persona | Orange actions | Commercial amount |
|---|---|---|
| Owner | Client List, Proposal Form, Contract Form, New Proposal | visible |
| Business Development | Client List, Contract Form, New Proposal | visible |
| Engineering | Proposal Form | hidden/read-protected |

The API enforces the same boundary through `actor_role`; the UI hides actions that the active persona cannot use. Engineering Proposal Form intake updates the canonical proposal to `PROPOSAL_HANDOVER`, which is visible to Business Development as the next commercial review state. The same opportunity/project record is used throughout; Engineering does not receive a second proposal record.
