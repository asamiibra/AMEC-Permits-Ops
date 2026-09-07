# Rebaseline V5 provenance supplement v1

This supplemental record preserves the historical Rebaseline V5 evidence without rewriting the accepted commit.

```text
ACCEPTED_REBASELINE_SHA=8dfcc55a48f44ba88ee5cb9fb9c0c7dd096f42dd
ACCEPTED_REBASELINE_BYTES_REWRITTEN=false
REBASELINE_ACCEPTANCE_REVOKED=false

ORIGINAL_V4_REQUIRED_MANIFEST_WAS_MISSING=true
ORIGINAL_V4_REQUIRED_VERSIONS_SUBDIR_WAS_MISSING=true
ORIGINAL_V4_PHYSICAL_LAYOUT_CONFORMS=false

LEGACY_59_FILE_BYTE_PARITY=PASS
SUPPLEMENTAL_PROVENANCE_CLOSURE=PASS

REBASELINE_SCHEMA_RUNTIME_RERUN_REQUIRED=false
```

The exact accepted commit physically contains 59 archived migration files at
`backend/migrations/history/postgresql_r13_0001_0059/`, but it does not contain
the V4-required `manifest.json` or `versions/` subdirectory. The supplement
records that mismatch as historical fact and proves byte parity against the
R13 source objects. It repairs provenance evidence sufficiency in this later
descendant; it does not claim that the accepted historical commit acquired
files it never contained.

The PostgreSQL rebaseline role is:

```text
POSTGRESQL_REBASELINE_ROLE=
HISTORICAL_MIGRATION_PROVENANCE
+ LOGICAL_SCHEMA_REFERENCE
+ CONTROL_DATA_REFERENCE
+ PORT_EQUIVALENCE_REFERENCE
```

It is not the current target-engine authority:

```text
POSTGRESQL_REBASELINE_ROLE_NOT=CURRENT_TARGET_ENGINE_AUTHORITY
DATABASE_TARGET_DECISION=OWNER_CONFIRMED
DATABASE_ENGINE_TARGET=AZURE_SQL_SQL_SERVER_ENGINE
AZURE_SQL_SERVICE_VARIANT=OWNER_DECISION_PENDING
```
