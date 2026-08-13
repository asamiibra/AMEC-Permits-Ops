# Dashboard Version Architecture

## V1 purpose

Dashboard V1 (`/dashboard`) is the stable legacy owner surface for normal existing content workflows. It preserves the pre-Wave-A library, filter, list, detail, and action experience.

## V2 purpose

Dashboard V2 (`/dashboard-v2`) is the active governance surface. Wave A lives here, including governance filters, provenance, currentness, quality, source sections, restricted-reference metadata, readiness, and governance Inputs & Go-Live.

## Shared truth

V1 and V2 share canonical master-content items, documents, document versions, purpose bindings, audit, material propagation, security, and downstream resolver identity. The UI route is not persisted on content records.

## Evolution policy

V1 is frozen except for security, critical defects, shared canonical behavior, or required compatibility fixes. V2 is the intended evolution surface for future regulatory applicability, requirement/rule lineage, form automation profiles, mapping releases, QA, and automated-readiness governance.

Those future waves remain deferred until the canonical shared foundations are implemented. This split does not create Dashboard-local substitutes for them.
