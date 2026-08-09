# Project / Synology / Excel Operating Contract

> **DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED**

Project creation begins from an explicit initiation event and confirmed reservation. PermitOps stores the exact project number and requires explicit resolution for mismatched external references.

Synology roots use `2026/PRJ-YYYY-NNN_Project-Name` with the canonical subfolders `01_Client`, `02_Property`, `03_Design`, `04_Permits`, and `05_Correspondence`. Discovery is metadata-oriented. PermitOps may create synthetic project roots/templates through the bootstrap seam but may not silently overwrite existing project content.

Excel is a shared operational representation, not canonical truth. The canonical workbook is `mock-systems/excel/permit_tracker.xlsx`; human sheets are read-only to the system. PermitOps writes only explicit columns in `PERMITOPS SYSTEM PROJECTION`, verifies the write, and audits it. A lock produces `WORKBOOK_LOCKED_MANUAL_COPY_REQUIRED`; there is no destructive retry loop.
