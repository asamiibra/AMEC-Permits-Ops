# API contract

Implemented routes include:

- `GET /api/master-content`, `POST /api/master-content`
- `GET /api/master-content?content_type=FORM` is the canonical Forms projection used by Dashboard and Administration (and the downstream work/BD/permit surfaces); Form mutations may identify their UI origin with `X-Source-Surface: DASHBOARD|ADMINISTRATION`.
- `GET /api/master-content/categories`
- `GET /api/master-content/{id}`, `/versions`, `/download`
- `POST /api/master-content/{id}/versions`, `/archive`, `/reconcile`
- `GET/POST /api/definitions`
- `GET /api/definitions/{id}`, `/revisions`
- `POST /api/definitions/{id}/revisions`, `/archive`

Typed failure codes include `MASTER_CONTENT_REF_CONFLICT`, `VERSION_CONFLICT`, `FILE_TYPE_NOT_ALLOWED`, `FILE_TOO_LARGE`, `SOR_UNAVAILABLE`, `SOR_DESTINATION_UNRESOLVED`, `SOR_HASH_MISMATCH`, `SOR_EXTERNAL_MUTATION`, `CONTENT_NOT_FOUND`, and `CAPABILITY_DENIED`.
