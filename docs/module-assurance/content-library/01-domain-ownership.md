# Domain Ownership Map

| Domain | Canonical owner | Content Library relationship |
|---|---|---|
| Reusable Forms | Content Library / Forms governance | Owns reusable Form definitions, source/version metadata, discovery, bindings, currentness and provenance. |
| Reports | Report/technical workflow | Content Library may expose reusable Report definitions/templates; an actual Technical Report is a controlled Project artifact. |
| Engineering Works | Engineering | Content Library stores reusable Engineering Work definitions; Engineering owns project revisions, approvals and baselines. |
| Definitions | Content Library / Definitions | Owns semantic Definition entries and revisions; it does not own client or project facts. |
| Requirements | Requirements engine / Project | Owns policies, requirement items, applicability and evaluation. Content Library can provide source Forms/Definitions. |
| Evidence | Evidence chain / Project | Owns documents, observations, verification, assertions and project evidence selections. |
| Permit / authority | Permit and Source18 | Owns AuthorityCase, official-form release, packet, sign/stamp/custody and submission outcomes. |
| Correspondence | Correspondence/Construction | Owns correspondence register and communication state. |
| Handover | Handover | Owns handover package and acceptance state. |
| Finance | Finance | Owns commercial/financial state. |

The seam rule is explicit: `reusable Checklist definition = Form`, while an operational Project checklist is a projection of canonical Project Requirement Items. No duplicate downstream system of record was added.
