"""Phase 3 aggregates + snapshots + jobs schema.

Revision ID: 20260213_01
Revises:
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260213_01"
down_revision = None
branch_labels = None
depends_on = None


def _jsonb_type():
    bind = op.get_bind()
    if bind and bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    op.create_table(
        "daily_cost_by_service",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("service", sa.Text(), nullable=False),
        sa.Column("cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False, server_default="USD"),
        sa.PrimaryKeyConstraint("date", "service"),
    )
    op.create_index("idx_daily_cost_by_service_date_service", "daily_cost_by_service", ["date", "service"])

    op.create_table(
        "monthly_cost_by_service",
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("service", sa.Text(), nullable=False),
        sa.Column("cost", sa.Numeric(18, 6), nullable=False),
        sa.PrimaryKeyConstraint("month", "service"),
    )
    op.create_index("idx_monthly_cost_by_service_month_service", "monthly_cost_by_service", ["month", "service"])

    op.create_table(
        "cost_by_compartment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("compartment_ocid", sa.Text(), nullable=True),
        sa.Column("compartment_name", sa.Text(), nullable=True),
        sa.Column("service", sa.Text(), nullable=True),
        sa.Column("cost", sa.Numeric(18, 6), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cost_by_compartment_date_compartment", "cost_by_compartment", ["date", "compartment_ocid"])

    op.create_table(
        "cost_by_resource",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("resource_ocid", sa.Text(), nullable=False),
        sa.Column("resource_name", sa.Text(), nullable=True),
        sa.Column("service", sa.Text(), nullable=True),
        sa.Column("compartment_ocid", sa.Text(), nullable=True),
        sa.Column("cost", sa.Numeric(18, 6), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cost_by_resource_resource_ocid", "cost_by_resource", ["resource_ocid"])
    op.create_index("idx_cost_by_resource_date_resource", "cost_by_resource", ["date", "resource_ocid"])

    op.create_table(
        "license_cost_table",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("license_type", sa.Text(), nullable=False),
        sa.Column("sku", sa.Text(), nullable=True),
        sa.Column("cost", sa.Numeric(18, 6), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_license_cost_table_date_license_type", "license_cost_table", ["date", "license_type"])

    op.create_table(
        "storage_waste_table",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("waste_type", sa.Text(), nullable=False),
        sa.Column("resource_ocid", sa.Text(), nullable=True),
        sa.Column("cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("details", _jsonb_type(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_storage_waste_table_date_waste_type", "storage_waste_table", ["date", "waste_type"])

    # Existing deployments may already have cost_snapshots. Add required phase-3 columns if missing.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "cost_snapshots" not in tables:
        op.create_table(
            "cost_snapshots",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("snapshot_uuid", sa.String(length=36), nullable=False),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("scope", _jsonb_type(), nullable=True),
            sa.Column("data", _jsonb_type(), nullable=True),
            sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_cost_snapshots_snapshot_uuid", "cost_snapshots", ["snapshot_uuid"], unique=True)
    else:
        cols = {c["name"] for c in inspector.get_columns("cost_snapshots")}
        if "snapshot_uuid" not in cols:
            op.add_column("cost_snapshots", sa.Column("snapshot_uuid", sa.String(length=36), nullable=True))
            op.create_index("idx_cost_snapshots_snapshot_uuid", "cost_snapshots", ["snapshot_uuid"], unique=False)
        if "name" not in cols:
            op.add_column("cost_snapshots", sa.Column("name", sa.Text(), nullable=True))
        if "scope" not in cols:
            op.add_column("cost_snapshots", sa.Column("scope", _jsonb_type(), nullable=True))
        if "data" not in cols:
            op.add_column("cost_snapshots", sa.Column("data", _jsonb_type(), nullable=True))
        if "computed_at" not in cols:
            op.add_column("cost_snapshots", sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("idx_cost_snapshots_name_computed_at", "cost_snapshots", ["name", "computed_at"], unique=False)

    op.create_table(
        "job_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("params", _jsonb_type(), nullable=True),
        sa.Column("result", _jsonb_type(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_job_runs_job_type", "job_runs", ["job_type"])
    op.create_index("idx_job_runs_status", "job_runs", ["status"])


def downgrade() -> None:
    op.drop_index("idx_job_runs_status", table_name="job_runs")
    op.drop_index("idx_job_runs_job_type", table_name="job_runs")
    op.drop_table("job_runs")
    op.drop_index("idx_cost_snapshots_name_computed_at", table_name="cost_snapshots")
    op.drop_index("idx_storage_waste_table_date_waste_type", table_name="storage_waste_table")
    op.drop_table("storage_waste_table")
    op.drop_index("idx_license_cost_table_date_license_type", table_name="license_cost_table")
    op.drop_table("license_cost_table")
    op.drop_index("idx_cost_by_resource_date_resource", table_name="cost_by_resource")
    op.drop_index("idx_cost_by_resource_resource_ocid", table_name="cost_by_resource")
    op.drop_table("cost_by_resource")
    op.drop_index("idx_cost_by_compartment_date_compartment", table_name="cost_by_compartment")
    op.drop_table("cost_by_compartment")
    op.drop_index("idx_monthly_cost_by_service_month_service", table_name="monthly_cost_by_service")
    op.drop_table("monthly_cost_by_service")
    op.drop_index("idx_daily_cost_by_service_date_service", table_name="daily_cost_by_service")
    op.drop_table("daily_cost_by_service")
