"""Phase 0 OCI security hotfix columns.

Revision ID: 20260222_10
Revises: 20260213_03
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260222_10"
down_revision = "20260213_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("settings", sa.Column("oci_last_test_status", sa.String(length=32), nullable=True))
    op.add_column("settings", sa.Column("oci_last_tested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("settings", sa.Column("oci_last_test_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("settings", "oci_last_test_error")
    op.drop_column("settings", "oci_last_tested_at")
    op.drop_column("settings", "oci_last_test_status")

