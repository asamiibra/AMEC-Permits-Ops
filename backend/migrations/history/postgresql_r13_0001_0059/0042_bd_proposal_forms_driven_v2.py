"""BD Proposal Forms-Driven v2 typed commercial/scoping companions."""

from alembic import op
import sqlalchemy as sa

from backend.app.models import Base


revision = "0042_bd_proposal_forms_driven_v2"
down_revision = "0041_dashboard_v2_waves_b_c"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    return column in {row["name"] for row in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _has_column("client_accounts", "canonical_party_id"):
        bind = op.get_bind()
        column = sa.Column(
            "canonical_party_id",
            sa.String(36),
            sa.ForeignKey("parties.id", name="fk_client_accounts_canonical_party_id_parties"),
            nullable=True,
        )
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("client_accounts", recreate="always") as batch:
                batch.add_column(column)
        else:
            op.add_column("client_accounts", column)
        op.create_index("ix_client_accounts_canonical_party_id", "client_accounts", ["canonical_party_id"])
    for name in (
        "proposal_contact_contexts",
        "proposal_site_contexts",
        "proposal_stakeholder_intents",
        "proposal_source_links",
        "proposal_service_scope_items",
        "proposal_regulatory_scope_intents",
        "proposal_assumptions",
        "proposal_external_cost_assumptions",
        "proposal_engineering_contributions",
        "proposal_expected_input_previews",
    ):
        Base.metadata.tables[name].create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for name in (
        "proposal_expected_input_previews",
        "proposal_engineering_contributions",
        "proposal_external_cost_assumptions",
        "proposal_assumptions",
        "proposal_regulatory_scope_intents",
        "proposal_service_scope_items",
        "proposal_source_links",
        "proposal_stakeholder_intents",
        "proposal_site_contexts",
        "proposal_contact_contexts",
    ):
        Base.metadata.tables[name].drop(bind=op.get_bind(), checkfirst=True)
    if _has_column("client_accounts", "canonical_party_id"):
        bind = op.get_bind()
        if "ix_client_accounts_canonical_party_id" in {row["name"] for row in sa.inspect(bind).get_indexes("client_accounts")}:
            op.drop_index("ix_client_accounts_canonical_party_id", table_name="client_accounts")
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("client_accounts", recreate="always") as batch:
                batch.drop_column("canonical_party_id")
        else:
            op.drop_column("client_accounts", "canonical_party_id")
