# Regulatory Journey and Permit UX

`RegulatoryJourney → AuthorityCase` remains one-to-many. Case creation accepts an existing project-matching journey or creates one; idempotency includes the journey selection. Portfolio rows expose `journey_id`/`journey_code`, case detail exposes journey and Parties & Representation, and New Permit exposes select/create journey context before case start. The default list remains one row per case because identifiers/comments are case-level. No one-case-per-project constraint was added.
