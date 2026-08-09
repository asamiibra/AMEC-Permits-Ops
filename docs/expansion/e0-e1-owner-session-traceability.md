# E0/E1 owner-session traceability

E0/E1 provides governance and semantic foundation. It does not complete downstream E2+ workflows. Every requirement remains `UNDECIDED_STAGE2` unless marked as a governance control below.

| ID | E0/E1 foundation | Reusable foundation | Status | E2+ remainder |
|---|---|---|---|---|
| OWN-NEW-01 | Opportunity/RFQ metadata | DocumentVersion, AuditEvent | FOUNDATION_COMPLETE | Intake runtime |
| OWN-NEW-02 | Opportunity owner field | User | FOUNDATION_COMPLETE | Ownership workflow |
| OWN-NEW-03 | Client account/contact | Shared evidence | FOUNDATION_COMPLETE | Client-data policy |
| OWN-NEW-04 | Quotation and revision | DocumentVersion, TemplateVersion | FOUNDATION_COMPLETE | Generation UX |
| OWN-NEW-05 | Typed CommercialTerm | Field/evidence controls | FOUNDATION_COMPLETE | Commercial review |
| OWN-NEW-06 | QuotationApproval association | Approval | FOUNDATION_COMPLETE | Release workflow |
| OWN-NEW-07 | Synthetic acceptance source family | EvidenceArtifact | FOUNDATION_PARTIAL_LATER_IMPLEMENTATION | Client response runtime |
| OWN-NEW-08 | Contract and revision | Approval, LineageEdge | FOUNDATION_COMPLETE | Contract setup workflow |
| OWN-NEW-09 | Immutable revision fields | LineageEdge | FOUNDATION_COMPLETE | Revision service |
| OWN-NEW-10 | ContractMilestone | Shared validity | FOUNDATION_COMPLETE | Milestone workflow |
| OWN-NEW-11 | ChecklistItem | RequirementConfig, DocumentValidity | FOUNDATION_COMPLETE | Checklist rules |
| OWN-NEW-12 | DocumentRequest | WorkflowTask, CommunicationDraft | FOUNDATION_COMPLETE | Request runtime |
| OWN-NEW-13 | ReferenceNumber bridge | Project/PermitApplication | FOUNDATION_COMPLETE | Numbering workflow |
| OWN-NEW-14 | ProjectAdministrationRecord | ExternalSystemLink | FOUNDATION_COMPLETE | Admin runtime |
| OWN-NEW-15 | Project-status representation metadata | Excel projection controls | FOUNDATION_PARTIAL_LATER_IMPLEMENTATION | Expanded Excel writes |
| OWN-NEW-16 | Shared DocumentVersion linkage | LineageEdge | FOUNDATION_COMPLETE | Attachment UX |
| OWN-NEW-17 | CommunicationDraft | Approval, Notification transport later | FOUNDATION_COMPLETE | Drafting UX |
| OWN-NEW-18 | CommunicationApproval | Approval | FOUNDATION_COMPLETE | Human release workflow |
| OWN-NEW-19 | Invoice and finance semantics | WorkflowTask | FOUNDATION_COMPLETE | Finance workflow |
| OWN-NEW-20 | InvoiceRevision | ContractMilestone | FOUNDATION_COMPLETE | Invoice generation |
| OWN-NEW-21 | Generic Finance Handoff | WorkflowTask | FOUNDATION_COMPLETE | Human finance routing |
| OWN-NEW-22 | EngineeringReview | DocumentVersion | FOUNDATION_COMPLETE | Selected discipline workflow |
| OWN-NEW-23 | DrawingReviewCycle | LineageEdge | FOUNDATION_COMPLETE | Review cycle runtime |
| OWN-NEW-24 | Regulation source/version/applicability | DocumentValidity | FOUNDATION_COMPLETE | Controlled source approval |
| OWN-NEW-25 | EngineeringComment | Approval, AuditEvent | FOUNDATION_COMPLETE | Engineer disposition |
| OWN-NEW-26 | ProjectHandover | RenderedArtifact | FOUNDATION_COMPLETE | Handover UX |
| OWN-NEW-27 | Handover approval field | Approval | FOUNDATION_COMPLETE | Release workflow |
| OWN-NEW-28 | Four assistant capability identities | Shared substrate | GOVERNANCE_CONTROLLED | Independent Stage 2 dispositions |
| OWN-NEW-29 | AI output policy metadata | Deterministic gates | GOVERNANCE_CONTROLLED | Capability implementation |
| OWN-NEW-30 | External action policy | Safety boundary | GOVERNANCE_CONTROLLED | Signed whitelist only |
| OWN-NEW-31 | Typed Stage 2 disposition contract | Governance config | GOVERNANCE_CONTROLLED | Owner decision |
| OWN-NEW-32 | TemplateDefinition/Version | Rendering controls | FOUNDATION_COMPLETE | Template freeze |
| OWN-NEW-33 | Shared evidence and lineage contract | Existing shared primitives | GOVERNANCE_CONTROLLED | Ongoing architecture control |
| OWN-NEW-34 | Shared Approval contract | Approval | GOVERNANCE_CONTROLLED | Ongoing approval policy |
| OWN-NEW-35 | Successor fixture and predecessor | Canonical fixture | FOUNDATION_COMPLETE | Future fixture deltas |
| OWN-NEW-36 | Role identifiers and authority metadata | Existing RBAC vocabulary | GOVERNANCE_CONTROLLED | RBAC approval |
| OWN-NEW-37 | Synthetic labels and safety checks | Synthetic-only policy | GOVERNANCE_CONTROLLED | Data-access decision |
| OWN-NEW-38 | HUMAN_SEND policy | CommunicationDraft | GOVERNANCE_CONTROLLED | Sign-off C whitelist |
| OWN-NEW-39 | TRACK/DRAFT/HANDOFF policy | AccountingHandoff | GOVERNANCE_CONTROLLED | Accounting decision |
| OWN-NEW-40 | Permit core regression protection | Original A12 and Golden Paths | GOVERNANCE_CONTROLLED | Mandatory continuity |

No quotation generation, contract execution, engineering AI, invoice issuance, handover release, email send, accounting write, authority write, or machine final submit is marked complete.
