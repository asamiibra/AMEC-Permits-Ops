# Filesystem and SQLite

The deployed read paths used PostgreSQL and DB-backed synthetic document bytes. The Vercel-specific safety patch prevents legacy SOR intake and Excel projection from writing to the deployment filesystem and routes synthetic Master Content bytes into durable `DocumentVersion.synthetic_content` instead.

`/tmp` is not used as a document system of record. SQLite is not active in the deployed environment.
