# Theme audit

The audit found three sources of visual drift: page-level hard-coded color clusters, inconsistent semantic emphasis between status/tag surfaces, and low-contrast muted copy on sparse pages. The remediation is a semantic token layer loaded after the prior productionization CSS.

## Findings and disposition

| Finding | Disposition |
|---|---|
| Deep navy structural identity existed but was not expressed as a final semantic family | Reconciled as `brand.primary` and `text.primary` |
| Teal accent was used for actions, links, and selected states with small variations | Reconciled as `brand.accent` plus interactive states |
| Neutral surfaces and borders varied by page | Reconciled as background and border families |
| Status colors were sometimes decorative rather than semantic | Restricted to success, warning, danger, and info roles |
| Muted helper copy was too light on representative screens | Darkened `text.secondary` and `text.muted`; Axe re-run passed |
| Shadows and rounded cards varied | Shared subtle/elevated shadow and radius rules applied |

No filter, route, workflow, or business behavior was changed to resolve these findings.
