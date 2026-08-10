# Register model

`/proposals-contracts?view=proposals` renders the Proposal register. `?view=contracts` renders the Contract register. Both receive the same six KPI values and the same validated SOR metadata. Proposal rows are derived from Opportunity plus its canonical reference and quotation. Contract rows are derived from Contract plus its quotation, related Opportunity, Project, and PermitApplication relationship.

The tables are separate projections, not a merged table with a type column. Amount and dates remain source-derived; absent governed values render as an em dash.
