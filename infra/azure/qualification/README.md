# G6 qualification topology

This is a temporary, qualification-only boundary derived from the G4 Azure
shape. It is not the production template and must be deployed to a fresh
resource group with a unique `qualificationId`.

The template creates only:

- a VNet with a delegated Container Apps subnet and a private-endpoint subnet;
- an internal Container Apps environment with separate runtime and migration
  jobs;
- a Standard ACR with public network access enabled, anonymous pulls disabled,
  admin credentials disabled, and managed-identity `AcrPull` assignments;
- an Azure SQL qualification server/database with public network access
  disabled, a private endpoint, and `privatelink.database.windows.net` DNS;
- distinct `QUAL_RUNTIME_UAMI` and `QUAL_MIGRATION_UAMI` identities; and
- short-retention Log Analytics diagnostics.

The SQL administrator parameter is control-plane bootstrap authority only. The
job URLs are constructed as credentialless `mssql+pyodbc` URLs, and the jobs
receive only their own attached UAMI client/principal IDs. The runtime job
executes `backend.app.g6_qualification_runtime`; the migration job executes
the governed `python -m backend.app.migrate` command.

Before deployment, capture a read-only subscription resource inventory with
`scripts/azure/g6_inventory_boundary.py capture`. After deployment, export the
qualification resource IDs and run its `validate` command. Keep both manifests
with the G6 evidence package; do not delete the boundary until independent G6
acceptance is complete.
