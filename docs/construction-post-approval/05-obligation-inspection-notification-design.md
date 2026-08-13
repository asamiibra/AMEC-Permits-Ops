# Obligations, Inspections, Notifications

Obligations have versioned definitions, instances, due rules, participant rows, and source references. A `WORK_START` definition becomes `DUE` only when a recorded `START` event occurs.

Notifications have prepared/sent evidence states and idempotency keys; sending is recorded, never performed by the application. Correspondence is a separate project record. Inspections explicitly use `INTERNAL_SITE` or `AUTHORITY`; a request or recorded internal inspection is not treated as an authority result.
