# People & Access

`GET /api/admin/users` projects seeded users, office, persona, and active state. `GET /api/admin/permissions` projects the capability matrix for Owner, Business Development, and Engineering.

Global Administration is available only to `SYSTEM_ADMIN` and `OWNER_SPONSOR`. Business Development and Engineering receive a 403 from every owner Administration API and are redirected away from direct Administration paths by the frontend. Production user provisioning is explicitly marked as requiring AMEC production setup.

The matrix keeps professional engineering authority, commercial release rules, credential handling, and final human Municipality submission as protected boundaries.
