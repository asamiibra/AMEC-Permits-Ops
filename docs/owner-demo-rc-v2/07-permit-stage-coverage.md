# Permit Stage Coverage

Stage 1 is verified end-to-end against PostgreSQL: the project workspace loads canonical identity and source links, the Confirm project & sources command POSTs to the backend, the response advances the workflow, and reload preserves Stage 2 / Verify Data.

The permit workspace contains deterministic stage projections through History / Close, with read-only Authority Review and explicit human-only final submission. Stage 1 is the release-critical persisted interaction; downstream stages remain controlled workspace projections and are not claimed as fully deployed-golden-path verified.
