# E2 rendering contract

`POST /api/render-requests` accepts governed context, verified fields, source revision IDs, and an optional template version. It returns a rendered artifact with immutable hashes, synthetic storage reference, status, and lineage.
