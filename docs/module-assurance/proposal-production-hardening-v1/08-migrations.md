# Migrations

Repository Alembic head after hardening: `proposal_production_hardening_v1`, down revision `17c6ebd99c4a`. The migration adds nullable bindings and its downgrade removes only those columns/constraints/indexes; it does not delete Proposal output history or document bytes. Migration graph/startup/round-trip checks pass in the isolated clone; one environment-gated migration check is skipped. Production database execution is not claimed.
