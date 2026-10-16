"""Persist subscription contracts, period checkpoints and source diagnostics."""

from alembic import op
import sqlalchemy as sa

revision = "20261017_01"
down_revision = "20260222_20"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "commitments_enabled" not in {
        row["name"] for row in inspector.get_columns("settings")
    }:
        op.add_column(
            "settings",
            sa.Column(
                "commitments_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )
    existing = set(inspector.get_table_names())
    if "subscription_contracts" not in existing:
        op.create_table(
            "subscription_contracts",
            sa.Column("id", sa.String(255), primary_key=True),
            sa.Column("source", sa.String(64), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(64), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("total_value", sa.Numeric(24, 8)),
            sa.Column("currency", sa.String(16), nullable=False),
            sa.Column("term_months", sa.Integer(), nullable=False),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "subscription_periods" not in existing:
        op.create_table(
            "subscription_periods",
            sa.Column("id", sa.String(255), primary_key=True),
            sa.Column("contract_id", sa.String(255), nullable=False),
            sa.Column("mode", sa.String(16), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("allowance", sa.Numeric(24, 8)),
            sa.Column("actual", sa.Numeric(24, 8)),
            sa.Column("forecast", sa.Numeric(24, 8)),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "contract_id", "mode", "start_date", name="uq_subscription_period"
            ),
        )
        op.create_index(
            "ix_subscription_periods_contract_id",
            "subscription_periods",
            ["contract_id"],
        )
    if "subscription_sync_runs" not in existing:
        op.create_table(
            "subscription_sync_runs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True)),
            sa.Column("sources", sa.JSON(), nullable=False),
        )


def downgrade():
    for name in (
        "subscription_periods",
        "subscription_sync_runs",
        "subscription_contracts",
    ):
        op.drop_table(name)
    op.drop_column("settings", "commitments_enabled")
