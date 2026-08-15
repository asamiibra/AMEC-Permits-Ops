# Browser evidence

Real local stack used: Vite `127.0.0.1:5175` with API `127.0.0.1:8002`, synthetic seeded database, and in-app browser.

Verified journey:

1. BD opened Opportunities → Proposal Register and saw All, Need Action, Authority Review, Ready / Close, explicit Client / Activity / Location fields, owner columns, and backend-derived counts.
2. New Proposal created with one Proposal identity and four source families uploaded through the canonical source controls.
3. Client Request, AMEC Scope, Process of Work, Additional Information, Price, Duration, and structured Proposal Breakdown content were saved.
4. Proceed moved the same Proposal to Engineering Preparation. Engineering persona saw commercial fields disabled while Process of Work and AMEC Scope remained editable; the technical update persisted on BD return.
5. BD saw resolved Dashboard Template / Checklist, Authority panel, accepted snapshot action, and output links after Accept.
6. Hard refresh returned to the register with the accepted Proposal in Ready / Close, then reopening the same row showed the exact pinned Proposal / Checklist versions and downloads.

The browser stack was synthetic/local only; no real Synology claim is made.
