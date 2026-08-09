# Multi-owner Domain Validation

> **DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED**

The canonical title deed creates one `Property`, two separate `Party` owners, two 1/2 `PropertyOwnership` records, and one separate representative party. `Representation` and `Authorization` are separate from ownership, with validity dates and `VALID` status. Arabic/English names and QID/CR-like identifiers remain source-preserving strings.

Property, owners, ownership shares, representation, authorization, source document version, source observation, and source assertion are exposed through `/api/reconciliation/properties/{project_id}`. There is no comma-separated owner shortcut.
