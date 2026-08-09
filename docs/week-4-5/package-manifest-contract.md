# Package Manifest Contract

Packages select exact current approved `DocumentVersion` records by configured document type/category. The manifest stores document-version IDs, category, SHA-256, revision, approval state, validity state, and order. `manifest_hash` and `source_truth_hash` make the package reproducible; filename-only selection is not used.
