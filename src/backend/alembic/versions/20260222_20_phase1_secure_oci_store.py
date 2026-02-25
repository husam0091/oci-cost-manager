"""Phase 1 secure OCI credential store.

Revision ID: 20260222_20
Revises: 20260222_10
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260222_20"
down_revision = "20260222_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oci_integrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_ocid", sa.String(length=255), nullable=False),
        sa.Column("tenancy_ocid", sa.String(length=255), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="degraded"),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "encrypted_secrets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("secret_name", sa.String(length=64), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("nonce", sa.Text(), nullable=False),
        sa.Column("salt", sa.Text(), nullable=False),
        sa.Column("key_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_encrypted_secrets_scope", "encrypted_secrets", ["scope"], unique=False)
    op.create_index("ix_encrypted_secrets_secret_name", "encrypted_secrets", ["secret_name"], unique=False)
    op.create_index("ix_encrypted_secrets_scope_name", "encrypted_secrets", ["scope", "secret_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_encrypted_secrets_scope_name", table_name="encrypted_secrets")
    op.drop_index("ix_encrypted_secrets_secret_name", table_name="encrypted_secrets")
    op.drop_index("ix_encrypted_secrets_scope", table_name="encrypted_secrets")
    op.drop_table("encrypted_secrets")
    op.drop_table("oci_integrations")

