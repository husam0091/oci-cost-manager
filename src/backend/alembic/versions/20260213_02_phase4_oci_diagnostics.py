"""Phase 4 OCI diagnostics table.

Revision ID: 20260213_02
Revises: 20260213_01
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260213_02"
down_revision = "20260213_01"
branch_labels = None
depends_on = None


def _jsonb_type():
    bind = op.get_bind()
    if bind and bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    op.create_table(
        "oci_diagnostics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("config_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("key_readable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenancy_reachable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("identity_api_reachable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("usage_api_reachable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cost_api_reachable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("regions", _jsonb_type(), nullable=True),
        sa.Column("tenancy_ocid", sa.Text(), nullable=True),
        sa.Column("user_ocid", sa.Text(), nullable=True),
        sa.Column("fingerprint", sa.Text(), nullable=True),
        sa.Column("last_sync_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("error", _jsonb_type(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_oci_diagnostics_checked_at_desc", "oci_diagnostics", ["checked_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_oci_diagnostics_checked_at_desc", table_name="oci_diagnostics")
    op.drop_table("oci_diagnostics")

