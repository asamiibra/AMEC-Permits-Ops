# Synology / Excel findings v0

## Synthetic Synology

- Assumed project root pattern: `2026/PRJ-number_Project-Name`.
- Logical taxonomy: `01_Client`, `02_Property`, `03_Design`, `04_Permits`, `05_Correspondence`.
- Filename/version limitation: the fixture uses simple revision-like names and does not infer a canonical version.
- Integration method currently mocked: local read-only filesystem adapter.
- Questions: Is the real root stable? Are permissions per project? Are files versioned? Which folder is authoritative? Can metadata be read without copying raw files?

## Synthetic Excel

- Workbook: `mock-systems/excel/permit_tracker.xlsx`.
- Sheet structure: `GENERAL FOLLOW UP`, `DESIGN`, `SUPERVISION`.
- Row identity: project number plus workbook sheet/row location.
- User-owned fields: status, notes, engineer assignment, and last update remain human mock data.
- Future system-owned fields should be separate from human sheets; the adapter is read-only in Week 1.
- Lock/concurrent-edit behavior is simulated by fixture documentation only; the workbook is not mutated.
- Excel must not become canonical truth because it is a shared operational representation with stale/inconsistent values and workbook lock behavior.

Validation questions: What is the actual row key? Which fields may PermitOps write? How are locks resolved? Who owns corrections? What is the retention/version history? Can a separate system-output sheet be approved?
