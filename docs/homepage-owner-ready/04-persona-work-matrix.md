# Work visibility matrix

| User | Visible work | Team control |
| --- | --- | --- |
| Owner | Union of applicable Owner, Business Development, Engineering, system, handoff, and unassigned work | Team filter: All, Business Development, Engineering, Owner, System / Other |
| Business Development | Commercial proposal, contract, communication review, and relevant handoffs | No team impersonation filter |
| Engineering | Proposal preparation, technical proposal work, permit work, findings, and relevant handoffs | No team impersonation filter |

The backend resolves development-role aliases to the same business visibility rules used by the projection. The owner-union test verifies scoped IDs are contained in the Owner result.
