# Idempotency and hashing proof

`backend/app/services/intelligence_contracts.py` centralizes canonical serialization and SHA-256 hashing:

```text
json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

Identity excludes database IDs, creation timestamps, and derived hashes. Repeating an idempotency key with identical canonical payload returns the original row. Reusing it with a materially different payload raises `INTELLIGENCE_IDEMPOTENCY_KEY_REUSE_MISMATCH`.

The service derives candidate `value_hash`, context `context_hash`, work-product `output_hash`, and citation `citation_hash` deterministically. Context dependency identity is unique by snapshot, dependency type, dependency ID, and version/hash. No prompt, raw source, full output, secret, or PII is admitted to the ledger or dependency metadata.
