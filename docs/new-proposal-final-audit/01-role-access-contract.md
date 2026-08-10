# Role access contract

The UI consumes the existing backend capability payload. Owner and Business Development can use New Proposal where the current capability model permits it. Engineering sees only Proposal Form on the portfolio and is denied New Proposal creation server-side.

Engineering direct API creation returns HTTP 403 with typed `CAPABILITY_DENIED`; the browser route returns the controlled message `New Proposal intake is handled by Business Development.`

Markers: `ENGINEERING_NEW_PROPOSAL_BLANK_PAGE_ZERO`, `ENGINEERING_CREATE_PROPOSAL_SERVER_DENIED`, `ENGINEERING_NEW_PROPOSAL_ACCESS_PASS`.
