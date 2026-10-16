"""Retain subscription financial lines underneath canonical terms."""

from alembic import op
import sqlalchemy as sa

revision = "20261017_02"
down_revision = "20261017_01"
branch_labels = None
depends_on = None


def upgrade():
    if "subscription_contract_lines" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "subscription_contract_lines",
            sa.Column("id", sa.String(255), primary_key=True),
            sa.Column("contract_id", sa.String(255), nullable=True),
            sa.Column(
                "source_contract_id", sa.String(255), nullable=False, unique=True
            ),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("total_value", sa.Numeric(24, 8)),
            sa.Column("currency", sa.String(16), nullable=False),
            sa.Column("status", sa.String(64), nullable=False),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_subscription_contract_lines_contract_id",
            "subscription_contract_lines",
            ["contract_id"],
        )


def downgrade():
    op.drop_table("subscription_contract_lines")
