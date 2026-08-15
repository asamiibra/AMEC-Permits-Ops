# Field authority map

| Surface | Owner | Editable fields |
|---|---|---|
| Client Request | BD / Owner | client, contact, description, client scope, budget, timing, constraints, additional information |
| Site / Property | BD / Owner | location, plot, area, area kind, site description |
| Engineering Preparation | Engineering / Owner | AMEC service scope, SOW, process, assumptions, deliverables, references, regulatory scoping, expected inputs |
| Commercial Review | BD commercial roles | fee, currency, duration, payment terms, validity, inclusions, exclusions, breakdown |
| Acceptance | authorized human | immutable accepted revision only |

Each section saves only its own field set. Client constraints use the dedicated `client_constraints` key (with legacy `exclusions` read as a fallback), while Commercial Exclusions remain `exclusions`; AMEC technical fields do not overwrite Client Request fields, and commercial fields are not exposed as an Engineering save operation.
