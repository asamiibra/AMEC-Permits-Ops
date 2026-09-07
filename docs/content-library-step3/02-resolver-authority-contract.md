# Resolver authority contract

The workflow-selection seam is separate from governed retrieval:

`governed_retrieve(...)` returns authorized evidence for search, citations, and read context. It is never a template selector.

`canonical_master_content_candidates(module, usage_type, content_type)` applies the existing policy dimensions: active binding and purpose, active item, `needs_review=false`, current pointer, `master_status=CURRENT`, reviewed version, available source reference, and applicable governance readiness. It returns all eligible candidates without choosing one.

`resolve_master_content_purpose(...)` returns `RESOLVED` for one candidate, `UNRESOLVED` for zero, and `AMBIGUOUS` for more than one. It never uses newest-row, title, filename, similarity, or AI selection.

`exact_master_content_binding_check(...)` validates a supplied item/version pair before a consumer is created or rendered. It cannot authorize an inactive, review, restricted, mismatched, non-current, or unreviewed source.
