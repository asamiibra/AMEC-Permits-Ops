# Domain Reconciliation

| Concept | Current canonical owner | Action | Reason |
|---|---|---|---|
| External body / jurisdiction / service | Regulatory Core | Reuse | Avoid duplicate regulatory identity. |
| Regulatory journey / authority case | Regulatory Core | Reuse and add runtime companions | Existing identity is the case anchor; runtime history belongs in companions. |
| Requirement definition / policy / groups | Requirement Engine v2 | Reuse | Policy remains governed and versioned. |
| Case requirement | New `RequirementInstance` | Add | Runtime realization of a policy item for one explicit case. |
| Evidence satisfaction | Requirement Engine evaluation + new case selection | Extend | A verified document is not automatically a case requirement result. |
| Physical original/sample | New `PhysicalEvidenceItem` | Add bounded seam | Digital and physical readiness must remain separate. |
| Forms / mapping / generated artifact | Form Automation runtime | Reuse | Pin exact source and mapping versions; no duplicate form engine. |
| Engineering baseline | ApprovedDesignBaseline | Reuse | Submission pins exact baseline/member/rendition; no latest-file lookup. |
| Preparation revision | New `PreparationRevision` | Add | Immutable case snapshot distinct from submission package. |
| Submission package | New `SubmissionPackage` / items | Add | Explicit manifest and checksum, not a folder. |
| Deterministic precheck | New `SubmissionPrecheckRun` / checks | Add | Backend-authoritative, reproducible gate. |
| Human submit / external confirmation | New attempt/snapshot/cycle companions | Add | Authorization is distinct from external receipt. |
| Findings / responses | New case-linked companions | Add | Existing Week 7 findings are application-oriented; this runtime needs exact case/cycle lineage. |
| External outcomes | Existing `AuthorityOutcome` | Reuse through case-linked runtime | No construction authorization is inferred. |
| Audit / lineage / My Work | Existing AuditEvent, LineageEdge, WorkflowTask seam | Reuse/extend | Consequential actions remain traceable. |
| Permit UI | Existing legacy workspace plus future routes | Bounded read model only | Do not build the full Permit product in this prompt. |

No duplicate `ExternalBody`, `Jurisdiction`, `ServiceType`, policy engine, form engine, Engineering baseline, DocumentVersion, Project, Party, or Property identity is introduced.
