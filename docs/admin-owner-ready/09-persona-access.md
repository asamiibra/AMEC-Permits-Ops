# Persona access result

| Persona | Normal nav | Direct `/admin` API | Outcome |
|---|---|---|---|
| Owner (`SYSTEM_ADMIN`, `OWNER_SPONSOR`) | Administration visible | 200 | Allowed |
| Business Development | Administration hidden | 403 `ADMINISTRATION_ACCESS_DENIED` | Denied |
| Engineering | Administration hidden | 403 `ADMINISTRATION_ACCESS_DENIED` | Denied |

This is enforced twice: the frontend does not render the privileged nav or retain direct owner paths for non-owner personas, and the backend dependency protects every `/api/admin/*` route.
