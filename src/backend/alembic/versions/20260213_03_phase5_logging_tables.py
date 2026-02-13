"""Phase 5 logging and audit tables.

Revision ID: 20260213_03
Revises: 20260213_02
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260213_03"
down_revision = "20260213_02"
branch_labels = None
depends_on = None


def _jsonb_type():
    bind = op.get_bind()
    if bind and bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    op.create_table(
        "log_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("log_type", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=True),
        sa.Column("route", sa.Text(), nullable=True),
        sa.Column("method", sa.Text(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("resource_ocid", sa.Text(), nullable=True),
        sa.Column("compartment_ocid", sa.Text(), nullable=True),
        sa.Column("service", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", _jsonb_type(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_log_events_ts_desc", "log_events", ["ts"], unique=False)
    op.create_index("idx_log_events_type_ts", "log_events", ["log_type", "ts"], unique=False)
    op.create_index("idx_log_events_correlation_id", "log_events", ["correlation_id"], unique=False)
    op.create_index("idx_log_events_job_id", "log_events", ["job_id"], unique=False)
    op.create_index("idx_log_events_level_ts", "log_events", ["level", "ts"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("meta", _jsonb_type(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_events_ts_desc", "audit_events", ["ts"], unique=False)
    op.create_index("idx_audit_events_actor_ts", "audit_events", ["actor", "ts"], unique=False)
    op.create_index("idx_audit_events_action_ts", "audit_events", ["action", "ts"], unique=False)
    op.create_index("idx_audit_events_correlation_id", "audit_events", ["correlation_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_audit_events_correlation_id", table_name="audit_events")
    op.drop_index("idx_audit_events_action_ts", table_name="audit_events")
    op.drop_index("idx_audit_events_actor_ts", table_name="audit_events")
    op.drop_index("idx_audit_events_ts_desc", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("idx_log_events_level_ts", table_name="log_events")
    op.drop_index("idx_log_events_job_id", table_name="log_events")
    op.drop_index("idx_log_events_correlation_id", table_name="log_events")
    op.drop_index("idx_log_events_type_ts", table_name="log_events")
    op.drop_index("idx_log_events_ts_desc", table_name="log_events")
    op.drop_table("log_events")
