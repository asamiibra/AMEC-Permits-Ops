# Endpoint Reuse Map

Reused canonical routes: `GET /api/admin/contracts`, `GET /api/admin/contracts/{id}`, `PATCH /api/admin/contracts/{id}`, `GET /api/admin/contracts/{id}/readiness`, `GET /api/admin/contracts/{id}/history`, `GET /api/admin/contracts/{id}/billing-context`, `POST /api/admin/contracts/{id}/authority`, `POST /api/admin/contracts/{id}/evidence`, `POST /api/admin/contracts/{id}/client-inputs`, `POST /api/admin/contracts/{id}/deliverables`, `POST /api/admin/contracts/{id}/commercial-terms`, and `POST /api/admin/contracts/{id}/activate-project`.

Delta commands/routes: `PATCH /api/admin/contracts/{id}/client-fields`, `POST /api/admin/contracts/{id}/documents`, `GET /api/admin/contracts/{id}/documents/{version_id}/download`, and `POST /api/admin/contracts/{id}/accept`.

Source reuse: accepted Proposal snapshots remain immutable; ClientAccount/ClientContact provide canonical party/contact values; Dashboard master content provides the Contract Template; Document/DocumentVersion plus ContractAdminEvidence provide exact document lineage. No duplicate client, project, contract, or template truth was introduced.
