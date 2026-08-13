# Route and navigation plan

| Route | Purpose | Source surface |
|---|---|---|
| `/permits` | Primary Owner permit portfolio | Permit UX portfolio projection |
| `/permits/new` | Guided New Permit / Start Authority Case | Canonical activated Project and authority catalogs |
| `/permits/{case_id}` | Overview workspace | Permit UX case projection |
| `/permits/{case_id}/{tab}` | Deep-linkable workspace tab | Same projection, tab-selected |
| `/proposals-contracts` | Existing commercial register | Legacy Proposal / Contract surface retained for continuity |
| `/authority-cases` | Technical preparation/submission case surface | Existing bounded Preparation + Submission Loop UI |

The navigation item labelled Permit opens `/permits`. Existing proposal and contract navigation remains separate. Deep links are rejected unless the current actor can access the project/case. The workspace provides links to Engineering for drawing/baseline changes and to the bounded preparation/submission surface for technical actions.

## Tab order

Overview → Project Details → Requirements → Documents → Drawings → Forms → Comments → Submission History → Permit / License → History.

Preparation & Precheck is an optional advanced link, not a duplicate tabular workflow. The portfolio lane filters are derived client controls over server-side query parameters.
