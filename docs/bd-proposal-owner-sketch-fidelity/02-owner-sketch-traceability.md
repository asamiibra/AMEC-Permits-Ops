# Owner-sketch traceability

| Owner concept | Final UI / domain mapping | Endpoint | Status |
|---|---|---|---|
| BD / Proposal | Proposal Register and one Proposal workspace | `GET /api/bd/proposals`, `GET /api/bd/proposals/{id}` | PASS |
| All / Need Action / Authority Review / Ready / Close | Derived backend owner lanes | `GET /api/bd/proposals?lane=` | PASS |
| Proposal Desc. / Project Ref / Stage / Amount / Last Activity / Open | Register primary columns | list projection | PASS |
| Client name + activity + location | Explicit backend search fields | `client`, `activity`, `location`, `q` | PASS |
| Tender Document / Email / Photo / Client data | Existing source-family actions | `POST /api/bd/proposals/{id}/sources` | PASS |
| Client / Atten / Mobile / Project description | Client, Proposal Contact, Mobile, Project Description | contact and Proposal projection | PASS |
| SOW / Client Scope / Area / Project photo | AMEC Scope, Client Requested Scope, Area / quantity basis, Site / Project Photos | canonical Proposal forms | PASS |
| Process of Work / Price / Duration | Engineering technical field and BD commercial fields | `PATCH /api/bd/proposals/{id}` | PASS |
| Breakdown | Projection over current scope/contribution entities | Proposal detail projection | PASS |
| Exclude / Include / Information | Commercial summary, Additional Information | Proposal fields | PASS |
| AMEC Input | Internal AMEC input with accepted snapshot lineage | Proposal fields + audit | PASS |
| Authority / Accept | Proposal Review / Authority and human Accept | accept policy + `/accept` | PASS |
| Proposal / Checklist Download | Accepted revision output links | `/outputs/proposal`, `/outputs/checklist` | PASS |

No new Proposal, Client, Project, Breakdown, AMEC Input, Template, or Checklist truth was introduced.
