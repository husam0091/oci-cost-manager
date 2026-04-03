"""SQLAlchemy models for persisted data."""
import uuid
from datetime import UTC, datetime
from sqlalchemy import (
    Boolean,
    Column,
    String,
    Integer,
    DateTime,
    Text,
    JSON,
    Float,
    UniqueConstraint,
    Date,
    Numeric,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB

from .database import Base


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, default=1)
    username = Column(String(128), nullable=False, default="admin")
    password_hash = Column(String(256), nullable=False, default="")
    scan_interval_hours = Column(Integer, nullable=False, default=8)
    oci_auth_mode = Column(String(32), nullable=False, default="profile")
    oci_config_profile = Column(String(128), nullable=False, default="DEFAULT")
    oci_config_file = Column(String(512), nullable=True)
    oci_user = Column(String(255), nullable=True)
    oci_fingerprint = Column(String(128), nullable=True)
    oci_tenancy = Column(String(255), nullable=True)
    oci_region = Column(String(64), nullable=True)
    oci_enabled_regions = Column(JSON, nullable=True)  # list of additional region strings
    oci_key_file = Column(String(512), nullable=True)
    oci_key_content = Column(Text, nullable=True)
    oci_pass_phrase = Column(String(512), nullable=True)
    oci_last_test_status = Column(String(32), nullable=True)
    oci_last_tested_at = Column(DateTime(timezone=True), nullable=True)
    oci_last_test_error = Column(Text, nullable=True)
    important_compartments = Column(JSON, nullable=True)
    important_compartment_ids = Column(JSON, nullable=True)
    important_include_children = Column(Boolean, nullable=False, default=True)
    notifications_email_enabled = Column(Boolean, nullable=False, default=False)
    notifications_smtp_host = Column(String(255), nullable=True)
    notifications_smtp_port = Column(Integer, nullable=True, default=587)
    notifications_smtp_username = Column(String(255), nullable=True)
    notifications_smtp_password = Column(String(512), nullable=True)
    notifications_email_from = Column(String(255), nullable=True)
    notifications_email_to = Column(JSON, nullable=True)
    notifications_webhook_enabled = Column(Boolean, nullable=False, default=False)
    notifications_webhook_url = Column(String(1024), nullable=True)
    notifications_webhook_dry_run = Column(Boolean, nullable=False, default=True)
    user_role = Column(String(32), nullable=False, default="admin")  # admin|finops|engineer|viewer
    allowed_teams = Column(JSON, nullable=True)
    allowed_apps = Column(JSON, nullable=True)
    allowed_envs = Column(JSON, nullable=True)
    allowed_compartment_ids = Column(JSON, nullable=True)
    enable_oci_executors = Column(Boolean, nullable=False, default=False)
    enable_destructive_actions = Column(Boolean, nullable=False, default=False)
    enable_budget_auto_eval = Column(Boolean, nullable=False, default=True)
    enable_demo_mode = Column(Boolean, nullable=False, default=False)
    portal_ssl_enabled = Column(Boolean, nullable=False, default=False)
    portal_ssl_mode = Column(String(32), nullable=True)
    portal_ssl_cert_path = Column(String(512), nullable=True)
    portal_ssl_key_path = Column(String(512), nullable=True)
    portal_ssl_chain_path = Column(String(512), nullable=True)
    portal_ssl_subject = Column(String(512), nullable=True)
    portal_ssl_issuer = Column(String(512), nullable=True)
    portal_ssl_expires_at = Column(DateTime(timezone=True), nullable=True)
    portal_ssl_updated_at = Column(DateTime(timezone=True), nullable=True)
    portal_ssl_last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class UserAccount(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(128), nullable=False, unique=True, index=True)
    password_hash = Column(String(256), nullable=False, default="")
    role = Column(String(32), nullable=False, default="viewer")  # admin|finops|engineer|viewer
    allowed_teams = Column(JSON, nullable=True)
    allowed_apps = Column(JSON, nullable=True)
    allowed_envs = Column(JSON, nullable=True)
    allowed_compartment_ids = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class ScanRun(Base):
    __tablename__ = "scan_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String(32), default="running")  # running|success|failed
    error_message = Column(Text)


class Compartment(Base):
    __tablename__ = "compartments"
    id = Column(String(255), primary_key=True)  # OCID
    name = Column(String(255), nullable=False)
    parent_id = Column(String(255), index=True)
    path = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ocid = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(64), index=True)
    compartment_id = Column(String(255), index=True)
    region = Column(String(64), index=True, nullable=True)
    status = Column(String(64))
    shape = Column(String(128))
    details = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AllocationRule(Base):
    __tablename__ = "allocation_rules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    match_type = Column(String(32), nullable=False)  # tag|compartment|resource_name|sku|image_name
    match_expression = Column(String(512), nullable=False)
    set_env = Column(String(64))
    set_team = Column(String(128))
    set_app = Column(String(128))
    priority = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CostSnapshot(Base):
    __tablename__ = "cost_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_uuid = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    # Phase 3 snapshot schema (primary contract)
    name = Column(String(128), index=True)
    scope = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    data = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow, index=True)
    # Legacy fields kept for backward compatibility
    period = Column(String(16), index=True)
    start_date = Column(DateTime, index=True)
    end_date = Column(DateTime, index=True)
    total = Column(Float, default=0)
    by_service = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = tuple([
        UniqueConstraint("period", "start_date", name="uq_cost_period_start"),
        Index("idx_cost_snapshots_name_computed_at", "name", "computed_at"),
    ])


class TrendPoint(Base):
    __tablename__ = "trend_points"
    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(7), index=True)  # YYYY-MM
    month_start = Column(DateTime, index=True)
    total_cost = Column(Float, default=0)
    by_service = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("month", name="uq_trend_month"),
    )


class Budget(Base):
    __tablename__ = "budgets"
    budget_id = Column(String(64), primary_key=True, default=lambda: f"bud_{uuid.uuid4().hex[:16]}")
    name = Column(String(255), nullable=False)
    scope_type = Column(String(32), nullable=False, index=True)  # global|compartment|team|app|env
    scope_value = Column(String(255), nullable=False, index=True)
    include_children = Column(Boolean, nullable=False, default=False)
    period = Column(String(16), nullable=False, default="monthly")
    limit_amount = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False, default="USD")
    growth_cap_pct = Column(Float, nullable=True)
    forecast_guardrail_pct = Column(Float, nullable=True)
    alert_thresholds = Column(JSON, nullable=False, default=[50, 75, 90, 100])
    compare_mode = Column(String(16), nullable=False, default="actual")
    enabled = Column(Boolean, nullable=False, default=True)
    notifications_enabled = Column(Boolean, nullable=False, default=False)
    owner = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=True, index=True)
    end_date = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BudgetAlertEvent(Base):
    __tablename__ = "budget_alert_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    budget_id = Column(String(64), nullable=False, index=True)
    period_key = Column(String(16), nullable=False, index=True)  # YYYY-MM
    alert_kind = Column(String(32), nullable=False)  # threshold|forecast
    threshold = Column(Integer, nullable=True)
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    payload = Column(JSON, nullable=True)
    __table_args__ = (
        UniqueConstraint("budget_id", "period_key", "alert_kind", "threshold", name="uq_budget_alert_dedupe"),
    )


class BudgetDailySnapshot(Base):
    __tablename__ = "budget_daily_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    budget_id = Column(String(64), nullable=False, index=True)
    snapshot_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    current_spend = Column(Float, nullable=False, default=0)
    utilization_pct = Column(Float, nullable=False, default=0)
    forecast_end_of_month = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("budget_id", "snapshot_date", name="uq_budget_snapshot_daily"),
    )


class ActionRequest(Base):
    __tablename__ = "action_requests"
    action_id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String(32), nullable=False, index=True)  # recommendation|budget_alert|manual
    category = Column(String(32), nullable=False, index=True)  # cleanup|resize|schedule|tag_fix|notify_only
    target_type = Column(String(32), nullable=False, index=True)  # volume|instance|backup|policy|tag
    target_ref = Column(JSON, nullable=False, default={})
    proposed_change = Column(JSON, nullable=False, default={})
    estimated_savings_monthly = Column(Float, nullable=False, default=0)
    confidence = Column(String(16), nullable=False, default="low")  # high|medium|low
    risk_level = Column(String(16), nullable=False, default="moderate")  # safe|moderate|high
    status = Column(
        String(32),
        nullable=False,
        default="draft",
        index=True,
    )  # draft|pending_approval|approved|rejected|queued|running|succeeded|failed|rolled_back
    requested_by = Column(String(255), nullable=True)
    approved_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActionEvent(Base):
    __tablename__ = "action_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)  # created|approved|executed|failed|rollback|comment
    message = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class DailyCostByService(Base):
    __tablename__ = "daily_cost_by_service"
    date = Column(Date, primary_key=True, nullable=False)
    service = Column(String(128), primary_key=True, nullable=False)
    cost = Column(Numeric(18, 6), nullable=False, default=0)
    currency = Column(String(16), nullable=False, default="USD")
    __table_args__ = (
        Index("idx_daily_cost_by_service_date_service", "date", "service"),
    )


class MonthlyCostByService(Base):
    __tablename__ = "monthly_cost_by_service"
    month = Column(Date, primary_key=True, nullable=False)
    service = Column(String(128), primary_key=True, nullable=False)
    cost = Column(Numeric(18, 6), nullable=False, default=0)
    __table_args__ = (
        Index("idx_monthly_cost_by_service_month_service", "month", "service"),
    )


class CostByCompartment(Base):
    __tablename__ = "cost_by_compartment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    compartment_ocid = Column(String(255), nullable=True, index=True)
    compartment_name = Column(String(255), nullable=True)
    service = Column(String(128), nullable=True)
    cost = Column(Numeric(18, 6), nullable=False, default=0)
    __table_args__ = (
        Index("idx_cost_by_compartment_date_compartment", "date", "compartment_ocid"),
    )


class CostByResource(Base):
    __tablename__ = "cost_by_resource"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    resource_ocid = Column(String(255), nullable=False, index=True)
    resource_name = Column(String(255), nullable=True)
    service = Column(String(128), nullable=True)
    compartment_ocid = Column(String(255), nullable=True, index=True)
    cost = Column(Numeric(18, 6), nullable=False, default=0)
    __table_args__ = (
        Index("idx_cost_by_resource_resource_ocid", "resource_ocid"),
        Index("idx_cost_by_resource_date_resource", "date", "resource_ocid"),
    )


class LicenseCostTable(Base):
    __tablename__ = "license_cost_table"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    license_type = Column(String(64), nullable=False, index=True)
    sku = Column(String(255), nullable=True)
    cost = Column(Numeric(18, 6), nullable=False, default=0)
    __table_args__ = (
        Index("idx_license_cost_table_date_license_type", "date", "license_type"),
    )


class StorageWasteTable(Base):
    __tablename__ = "storage_waste_table"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    waste_type = Column(String(64), nullable=False, index=True)
    resource_ocid = Column(String(255), nullable=True, index=True)
    cost = Column(Numeric(18, 6), nullable=False, default=0)
    details = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    __table_args__ = (
        Index("idx_storage_waste_table_date_waste_type", "date", "waste_type"),
    )


class JobRun(Base):
    __tablename__ = "job_runs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="queued", index=True)
    progress = Column(Integer, nullable=False, default=0)
    params = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    result = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class OciDiagnostics(Base):
    __tablename__ = "oci_diagnostics"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(32), nullable=False, default="degraded")
    config_detected = Column(Boolean, nullable=False, default=False)
    key_readable = Column(Boolean, nullable=False, default=False)
    tenancy_reachable = Column(Boolean, nullable=False, default=False)
    identity_api_reachable = Column(Boolean, nullable=False, default=False)
    usage_api_reachable = Column(Boolean, nullable=False, default=False)
    cost_api_reachable = Column(Boolean, nullable=False, default=False)
    regions = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    tenancy_ocid = Column(String(255), nullable=True)
    user_ocid = Column(String(255), nullable=True)
    fingerprint = Column(String(128), nullable=True)
    last_sync_time = Column(DateTime, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    message = Column(Text, nullable=True)
    error = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    correlation_id = Column(String(128), nullable=True)
    __table_args__ = (
        Index("idx_oci_diagnostics_checked_at_desc", "checked_at"),
    )


class OciIntegration(Base):
    __tablename__ = "oci_integrations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_ocid = Column(String(255), nullable=False)
    tenancy_ocid = Column(String(255), nullable=False)
    fingerprint = Column(String(128), nullable=False)
    region = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="degraded")
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(255), nullable=False)
    updated_by = Column(String(255), nullable=False)


class EncryptedSecret(Base):
    __tablename__ = "encrypted_secrets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(String(64), nullable=False, index=True)
    secret_name = Column(String(64), nullable=False, index=True)
    ciphertext = Column(Text, nullable=False)
    nonce = Column(Text, nullable=False)
    salt = Column(Text, nullable=False)
    key_version = Column(String(32), nullable=False, default="v1")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    rotated_at = Column(DateTime(timezone=True), nullable=True)


class LogEvent(Base):
    __tablename__ = "log_events"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ts = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    level = Column(String(16), nullable=False, default="info", index=True)
    log_type = Column(String(32), nullable=False, index=True)
    source = Column(String(64), nullable=False, index=True)
    actor = Column(String(255), nullable=True)
    route = Column(String(512), nullable=True)
    method = Column(String(16), nullable=True)
    status_code = Column(Integer, nullable=True)
    correlation_id = Column(String(128), nullable=False, index=True)
    request_id = Column(String(128), nullable=True)
    job_id = Column(String(36), nullable=True, index=True)
    resource_ocid = Column(String(255), nullable=True)
    compartment_ocid = Column(String(255), nullable=True)
    service = Column(String(128), nullable=True)
    message = Column(Text, nullable=False)
    details = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    __table_args__ = (
        Index("idx_log_events_ts_desc", "ts"),
        Index("idx_log_events_type_ts", "log_type", "ts"),
        Index("idx_log_events_correlation_id", "correlation_id"),
        Index("idx_log_events_job_id", "job_id"),
        Index("idx_log_events_level_ts", "level", "ts"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ts = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    actor = Column(String(255), nullable=False)
    action = Column(String(64), nullable=False, index=True)
    target = Column(String(255), nullable=True)
    correlation_id = Column(String(128), nullable=False, index=True)
    meta = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    __table_args__ = (
        Index("idx_audit_events_ts_desc", "ts"),
        Index("idx_audit_events_actor_ts", "actor", "ts"),
        Index("idx_audit_events_action_ts", "action", "ts"),
        Index("idx_audit_events_correlation_id", "correlation_id"),
    )
