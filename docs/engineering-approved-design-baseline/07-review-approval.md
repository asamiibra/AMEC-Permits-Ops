# Review and professional approval

Status: `PROTECTED_AND_REGRESSION_VERIFIED`

Upload/ingest, review, finding disposition, and professional approval are separate states. Blocking findings, incomplete review, missing native/published rendition, failed/unknown technical checks, missing credential reference, and same-actor preparation/approval are blocking conditions. Approval pins exact rendition IDs and makes the business revision immutable.

Canonical `ProfessionalCredential` can be referenced and is validated for project and current status when supplied. A generic human credential reference remains the safe owner-decision seam because this repository has no PartyCredential table.
