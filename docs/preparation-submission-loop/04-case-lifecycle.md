# 04 · Authority Case lifecycle

Status: IMPLEMENTED

Authority Cases are created only through the explicit case endpoint with canonical active External Body, Jurisdiction, Service Type, activated Project context, and an idempotency key. Proposal acceptance, Project activation, and Engineering baseline approval do not create cases.

Internal states and external confirmation states are stored and projected separately. No case status claims submission before an `ExternalSubmissionSnapshot` and `AuthoritySubmissionCycle` exist.
