# Backup / restore rehearsal plan

Scope: PostgreSQL database, current evidence/artifact references, configuration bundles and manifests, audit events, and operational settings. The TEST manifest records local synthetic references and schema head `0015_week14_acceptance`.

The procedure is: obtain TEST backup set → restore isolated database → validate migration head, critical tables, foreign keys, audit reconstruction, fixture/config hashes, package/revision bindings, Finding/Resolution history, snapshots, and monitoring policy state. A successful dry run is `TEST_RESTORE_REHEARSAL`, never formal G10.
