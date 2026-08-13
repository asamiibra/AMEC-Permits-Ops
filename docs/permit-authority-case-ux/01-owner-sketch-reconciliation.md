# Owner-sketch reconciliation

## Scope

This UX is an Owner-facing projection over the existing authority-case, regulatory, evidence, engineering-baseline, forms, preparation, submission, findings, outcome, audit, and lineage models. It does not introduce Permit-local source-of-truth entities.

## Reconciled surfaces

| Owner sketch intent | Implemented surface | Reconciliation / safe default |
|---|---|---|
| Sketch 10 permit portfolio | `/permits` portfolio with derived lanes, search, filters, pagination, stage, system status, blocker summary, open-comment count | Permit number comes only from `AuthorityCaseIdentifier`; absent values render `Pending`. End Date is shown as unavailable until a canonical target-date semantic is proven. |
| Sketch 11 new permit | `/permits/new` guided start over an activated `Project` | Project is selected from canonical activated projects. External body, jurisdiction, and service are explicit choices. Accepted proposal scope is advisory context only. |
| Sketch 12 case workspace | `/permits/{case_id}` tabbed workspace | Tabs are read models assembled from canonical records; technical preparation/submission controls remain available through the bounded Authority Case surface. |
| Project and client details | Project, accepted Proposal/Contract, Party, Property, PropertyOwnership, VerifiedAssertion, DocumentVersion | No duplicate project, client, property, document, or ownership tables. Sensitive identifiers are masked by default. |
| Requirements and blockers | `RequirementInstance`, policy version, evidence evaluation/selection, precheck, physical gate, issues/findings | Friendly statuses are projected; policy detail is a drawer-level explanation, not a second requirement model. |
| Documents and drawings | `DocumentVersion` plus evidence selection; `ApprovedDesignBaseline` → member → `EngineeringDeliverableRevision` → rendition → `DocumentVersion` | Drawing revision is explicit. There is no “latest” shortcut. Update actions link back to Engineering. |
| Forms | `FormInstance`, automation profile, mapping release, rendered artifacts | Automated/manual origin is explicit. Generated output never auto-satisfies a requirement; signatures and stamps remain human actions. |
| Comments | `AuthorityCaseFinding` and response records | Internal response and external authority closure are separate. AI suggestions are advisory and never authoritative. |
| Submission history | immutable preparation revisions, packages, prechecks, attempts, snapshots, cycles | Pending external confirmation is not displayed as Submitted. |
| Permit / License | `AuthorityCaseOutcome`, authority identifiers, authority document version | System summary is labeled as such. No official permit is fabricated, and approval is not construction authorization. |
| Reports / Excel | projection export with safe columns and lineage metadata | No writes to `mock-systems/excel`; exports are permission-controlled and generated in memory. |

## Owner-sketch decisions and gaps

- Review Category is not conflated with Engineering Discipline. The current engineering baseline exposes discipline but no canonical `EngineeringReviewCategory`; the UX labels the available field accurately and records the category gap rather than inventing a value.
- “DC” is displayed only where the source record provides it; it is not inferred from an internal ID.
- End Date is `Not configured` unless a canonical authority target date is present.
- Lanes are derived views (`All Permits`, `Need Action`, `Authority Review`, `Ready / Close`), not persisted workflow statuses.
- System Status and Block are projections from current evidence, precheck, physical gate, baseline, finding, and submission state. Users cannot set a manual blocker flag.
- Exact deployed SHA remains externally unproven at this entry. The release will therefore use the UX code-freeze token unless deployment provenance is supplied.

## Fidelity acceptance

The implementation is accepted when each sketch surface has a reachable route, a canonical source mapping, a visible empty/loading/error state, and a browser evidence record. Any intentionally unavailable field is labeled rather than filled with a plausible placeholder.
