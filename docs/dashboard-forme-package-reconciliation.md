# Owner FORME package reconciliation

The supplied `FORME.zip` is treated as a read-only source package, not as a
Dashboard data dump. The repository remains synthetic-only, so the binaries
are not copied into the checked-in database or synthetic storage.

The Owner-facing implementation now supports the safe promotion path:

1. retain the original package and source path outside the master library;
2. classify each file as reusable candidate, historical/project evidence,
   reference evidence, or blocked reconciliation source;
3. promote only an Owner-approved reusable candidate through the normal Form
   upload path;
4. seed a candidate as `Needs Review` when it is visible for review but must
   not be selected by downstream resolvers; and
5. clear the short review note only after the Owner has corrected or approved
   the candidate.

The package audit identified 23 files and one intentionally empty
`CHECK LISTE FORME/MODIFICATION` folder. The safe master candidates are the
official Municipality undertakings/authorizations, the GSAS undertaking,
the Kahramaa U-value sheet, the TLC checklist after reconciliation, the
Building Completion/Maintenance/New Building checklists after cleanup, the
material conformity image only if explicitly accepted, the handover form,
and the invoice template after restricted-content review.

The following are deliberately not auto-promoted: completed or signed CC
documents, the completed Service Request, the TLC screenshot, the duplicate
Civil Defense/Change Activity pair, the dated custom contractor undertaking,
and the empty Modification folder. No supplied file is mapped to Reports,
Engineering Works, or Definitions by filename alone.

This keeps one canonical path:

`MasterContentItem(FORM) → Document → immutable DocumentVersion → configured
binary store`

Administration reads the same records as Dashboard. Permit, Engineering,
Completion/Handover, and Billing consume canonical versions through existing
bindings; Dashboard `Used In` remains informational and does not create
transactional requiredness.
