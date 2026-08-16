# Main Candidate

Candidate SHA: `4aedcc6c79973055aea14bb717c12a6dcb347953`.

The candidate is based on `origin/main` and contains normal merge commits for the owner Dashboard closure/provenance branch, Home navigation branch, and UI productionization branch. `origin/main` and all three feature heads are ancestors. The merge rehearsal and actual candidate merges had zero conflicts. Required current module work is reachable from the candidate; no current module has an unknown code location.

Candidate gates: Alembic single head PASS; fresh PostgreSQL migration PASS; staged upgrade migration PASS; PostgreSQL backend PASS; frontend PASS; build PASS; cross-module browser PASS; storage/source-intake PASS. The browser bundle covers Work, Dashboard, Dashboard V2 compatibility redirects, Forms, Reports, Engineering Works, Definitions, Inputs & Go-Live, Administration, Proposal, Contract, and shared Permit/regulatory foundation routes.
