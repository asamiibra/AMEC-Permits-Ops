# Attachment Idempotency Contract

The deterministic key is application + preparation revision + category + DocumentVersion. Retried association calls return the original intent and do not create duplicate associations.
