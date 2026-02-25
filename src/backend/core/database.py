"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator

from .config import get_settings

settings = get_settings()

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    _ensure_phase3_schema()
    _ensure_allocation_rules_table()
    _ensure_budget_tables()
    _ensure_action_tables()
    _ensure_settings_schema()
    _ensure_resource_schema()
    _ensure_phase4_schema()
    _ensure_phase5_schema()
    _ensure_sqlite_indexes()


def ensure_settings_schema() -> None:
    """Public wrapper for settings schema compatibility patching."""
    _ensure_settings_schema()


def _ensure_settings_schema() -> None:
    """Add newer settings columns for existing databases (best-effort)."""
    try:
        inspector = inspect(engine)
        if "settings" not in inspector.get_table_names():
            return

        existing = {col["name"] for col in inspector.get_columns("settings")}
        statements = []

        if "oci_config_profile" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_config_profile VARCHAR(128) DEFAULT 'DEFAULT'")
        if "oci_config_file" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_config_file VARCHAR(512)")
        if "oci_auth_mode" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_auth_mode VARCHAR(32) DEFAULT 'profile'")
        if "oci_user" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_user VARCHAR(255)")
        if "oci_fingerprint" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_fingerprint VARCHAR(128)")
        if "oci_tenancy" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_tenancy VARCHAR(255)")
        if "oci_region" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_region VARCHAR(64)")
        if "oci_key_file" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_key_file VARCHAR(512)")
        if "oci_key_content" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_key_content TEXT")
        if "oci_pass_phrase" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_pass_phrase VARCHAR(512)")
        if "oci_last_test_status" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_last_test_status VARCHAR(32)")
        if "oci_last_tested_at" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_last_tested_at DATETIME")
        if "oci_last_test_error" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN oci_last_test_error TEXT")
        if "important_compartment_ids" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN important_compartment_ids JSON")
        if "important_compartments" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN important_compartments JSON")
        if "important_include_children" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN important_include_children BOOLEAN DEFAULT 1")
        if "notifications_email_enabled" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN notifications_email_enabled BOOLEAN DEFAULT 0")
        if "notifications_smtp_host" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN notifications_smtp_host VARCHAR(255)")
        if "notifications_smtp_port" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN notifications_smtp_port INTEGER DEFAULT 587")
        if "notifications_smtp_username" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN notifications_smtp_username VARCHAR(255)")
        if "notifications_smtp_password" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN notifications_smtp_password VARCHAR(512)")
        if "notifications_email_from" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN notifications_email_from VARCHAR(255)")
        if "notifications_email_to" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN notifications_email_to JSON")
        if "notifications_webhook_enabled" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN notifications_webhook_enabled BOOLEAN DEFAULT 0")
        if "notifications_webhook_url" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN notifications_webhook_url VARCHAR(1024)")
        if "notifications_webhook_dry_run" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN notifications_webhook_dry_run BOOLEAN DEFAULT 1")
        if "user_role" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN user_role VARCHAR(32) DEFAULT 'admin'")
        if "allowed_teams" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN allowed_teams JSON")
        if "allowed_apps" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN allowed_apps JSON")
        if "allowed_envs" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN allowed_envs JSON")
        if "allowed_compartment_ids" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN allowed_compartment_ids JSON")
        if "enable_oci_executors" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN enable_oci_executors BOOLEAN DEFAULT 0")
        if "enable_destructive_actions" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN enable_destructive_actions BOOLEAN DEFAULT 0")
        if "enable_budget_auto_eval" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN enable_budget_auto_eval BOOLEAN DEFAULT 1")
        if "enable_demo_mode" not in existing:
            statements.append("ALTER TABLE settings ADD COLUMN enable_demo_mode BOOLEAN DEFAULT 0")

        if statements:
            with engine.begin() as conn:
                for stmt in statements:
                    conn.execute(text(stmt))
    except Exception:
        # Do not block app startup if schema patching fails.
        pass


def _ensure_allocation_rules_table() -> None:
    """Ensure allocation rules table exists even for legacy metadata load orders."""
    if "sqlite" not in settings.database_url:
        return
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS allocation_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(255) NOT NULL,
                        is_enabled BOOLEAN NOT NULL DEFAULT 1,
                        match_type VARCHAR(32) NOT NULL,
                        match_expression VARCHAR(512) NOT NULL,
                        set_env VARCHAR(64),
                        set_team VARCHAR(128),
                        set_app VARCHAR(128),
                        priority INTEGER NOT NULL DEFAULT 100,
                        created_at DATETIME,
                        updated_at DATETIME
                    )
                    """
                )
            )
    except Exception:
        pass


def _ensure_budget_tables() -> None:
    """Ensure budget tables exist for legacy deployments."""
    if "sqlite" not in settings.database_url:
        return
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS budgets (
                        budget_id VARCHAR(64) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        scope_type VARCHAR(32) NOT NULL,
                        scope_value VARCHAR(255) NOT NULL,
                        include_children BOOLEAN NOT NULL DEFAULT 0,
                        period VARCHAR(16) NOT NULL DEFAULT 'monthly',
                        limit_amount FLOAT NOT NULL,
                        currency VARCHAR(8) NOT NULL DEFAULT 'USD',
                        growth_cap_pct FLOAT,
                        forecast_guardrail_pct FLOAT,
                        alert_thresholds JSON NOT NULL,
                        compare_mode VARCHAR(16) NOT NULL DEFAULT 'actual',
                        enabled BOOLEAN NOT NULL DEFAULT 1,
                        notifications_enabled BOOLEAN NOT NULL DEFAULT 0,
                        owner VARCHAR(255) NOT NULL,
                        created_at DATETIME,
                        updated_at DATETIME
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS budget_alert_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        budget_id VARCHAR(64) NOT NULL,
                        period_key VARCHAR(16) NOT NULL,
                        alert_kind VARCHAR(32) NOT NULL,
                        threshold INTEGER,
                        triggered_at DATETIME,
                        payload JSON
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS budget_daily_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        budget_id VARCHAR(64) NOT NULL,
                        snapshot_date VARCHAR(10) NOT NULL,
                        current_spend FLOAT NOT NULL DEFAULT 0,
                        utilization_pct FLOAT NOT NULL DEFAULT 0,
                        forecast_end_of_month FLOAT NOT NULL DEFAULT 0,
                        created_at DATETIME
                    )
                    """
                )
            )
            # Legacy budgets table may exist without notifications_enabled.
            try:
                cols = {c["name"] for c in inspect(engine).get_columns("budgets")}
                if "notifications_enabled" not in cols:
                    conn.execute(text("ALTER TABLE budgets ADD COLUMN notifications_enabled BOOLEAN DEFAULT 0"))
            except Exception:
                pass
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_alert_budget ON budget_alert_events(budget_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_alert_period ON budget_alert_events(period_key)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_budget_alert_dedupe_idx ON budget_alert_events(budget_id, period_key, alert_kind, threshold)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_snapshot_budget ON budget_daily_snapshots(budget_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_snapshot_date ON budget_daily_snapshots(snapshot_date)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_budget_snapshot_daily_idx ON budget_daily_snapshots(budget_id, snapshot_date)"))
    except Exception:
        pass


def _ensure_action_tables() -> None:
    """Ensure action request/event tables exist for Phase 5 automation hooks."""
    if "sqlite" not in settings.database_url:
        return
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS action_requests (
                        action_id VARCHAR(64) PRIMARY KEY,
                        source VARCHAR(32) NOT NULL,
                        category VARCHAR(32) NOT NULL,
                        target_type VARCHAR(32) NOT NULL,
                        target_ref JSON NOT NULL,
                        proposed_change JSON NOT NULL,
                        estimated_savings_monthly FLOAT NOT NULL DEFAULT 0,
                        confidence VARCHAR(16) NOT NULL DEFAULT 'low',
                        risk_level VARCHAR(16) NOT NULL DEFAULT 'moderate',
                        status VARCHAR(32) NOT NULL DEFAULT 'draft',
                        requested_by VARCHAR(255),
                        approved_by VARCHAR(255),
                        created_at DATETIME,
                        updated_at DATETIME
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS action_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_id VARCHAR(64) NOT NULL,
                        event_type VARCHAR(32) NOT NULL,
                        message TEXT,
                        payload JSON,
                        timestamp DATETIME
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_actions_status ON action_requests(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_actions_category ON action_requests(category)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_actions_created ON action_requests(created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_action_events_action ON action_events(action_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_action_events_ts ON action_events(timestamp)"))
    except Exception:
        pass


def _ensure_resource_schema() -> None:
    """Add confidence fields for legacy DBs and backfill defaults."""
    if "sqlite" not in settings.database_url:
        return
    try:
        inspector = inspect(engine)
        if "resources" not in inspector.get_table_names():
            return
        existing = {col["name"] for col in inspector.get_columns("resources")}
        statements = []
        if "env" not in existing:
            statements.append("ALTER TABLE resources ADD COLUMN env VARCHAR(64)")
        if "team" not in existing:
            statements.append("ALTER TABLE resources ADD COLUMN team VARCHAR(128)")
        if "app" not in existing:
            statements.append("ALTER TABLE resources ADD COLUMN app VARCHAR(128)")
        if "allocation_confidence" not in existing:
            statements.append("ALTER TABLE resources ADD COLUMN allocation_confidence VARCHAR(16)")
        if "allocation_reason" not in existing:
            statements.append("ALTER TABLE resources ADD COLUMN allocation_reason VARCHAR(255)")
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
            # Backfill defaults for existing rows.
            conn.execute(text("UPDATE resources SET env = COALESCE(env, 'Unallocated')"))
            conn.execute(text("UPDATE resources SET team = COALESCE(team, 'Unallocated')"))
            conn.execute(text("UPDATE resources SET app = COALESCE(app, 'Unallocated')"))
            conn.execute(text("UPDATE resources SET allocation_confidence = COALESCE(allocation_confidence, 'low')"))
            conn.execute(text("UPDATE resources SET allocation_reason = COALESCE(allocation_reason, 'legacy_backfill')"))
            # Keep JSON details safe for callers that rely on details-only mapping metadata.
            try:
                conn.execute(
                    text(
                        "UPDATE resources SET details = json_set(COALESCE(details, '{}'), '$.env', COALESCE(env, 'Unallocated'), '$.team', COALESCE(team, 'Unallocated'), '$.app', COALESCE(app, 'Unallocated'), '$.allocation_confidence', COALESCE(allocation_confidence, 'low'), '$.allocation_reason', COALESCE(allocation_reason, 'legacy_backfill'))"
                    )
                )
            except Exception:
                # JSON1 may not be available in every SQLite build.
                pass
    except Exception:
        pass


def _ensure_sqlite_indexes() -> None:
    """Create performance indexes for aggregate workloads (idempotent)."""
    try:
        if "sqlite" not in settings.database_url:
            return
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        index_specs: list[tuple[str, str, str]] = [
            ("resources", "idx_resources_compartment", "CREATE INDEX IF NOT EXISTS idx_resources_compartment ON resources(compartment_id)"),
            ("resources", "idx_resources_type", "CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(type)"),
            ("resources", "idx_resources_updated", "CREATE INDEX IF NOT EXISTS idx_resources_updated ON resources(updated_at)"),
            ("resources", "idx_resources_env", "CREATE INDEX IF NOT EXISTS idx_resources_env ON resources(env)"),
            ("resources", "idx_resources_team", "CREATE INDEX IF NOT EXISTS idx_resources_team ON resources(team)"),
            ("resources", "idx_resources_app", "CREATE INDEX IF NOT EXISTS idx_resources_app ON resources(app)"),
            ("resources", "idx_resources_alloc_conf", "CREATE INDEX IF NOT EXISTS idx_resources_alloc_conf ON resources(allocation_confidence)"),
            ("cost_snapshots", "idx_cost_snapshots_period_start", "CREATE INDEX IF NOT EXISTS idx_cost_snapshots_period_start ON cost_snapshots(period, start_date)"),
            ("cost_snapshots", "idx_cost_snapshots_end", "CREATE INDEX IF NOT EXISTS idx_cost_snapshots_end ON cost_snapshots(end_date)"),
            ("scan_runs", "idx_scan_runs_started", "CREATE INDEX IF NOT EXISTS idx_scan_runs_started ON scan_runs(started_at)"),
            # Optional cost-line style tables if present in extended deployments.
            ("cost_lines", "idx_cost_lines_date_service", "CREATE INDEX IF NOT EXISTS idx_cost_lines_date_service ON cost_lines(usage_date, service)"),
            ("cost_lines", "idx_cost_lines_compartment", "CREATE INDEX IF NOT EXISTS idx_cost_lines_compartment ON cost_lines(compartment_id)"),
            ("cost_lines", "idx_cost_lines_resource", "CREATE INDEX IF NOT EXISTS idx_cost_lines_resource ON cost_lines(resource_id)"),
            ("cost_line_items", "idx_cost_line_items_date_service", "CREATE INDEX IF NOT EXISTS idx_cost_line_items_date_service ON cost_line_items(usage_date, service)"),
            ("cost_line_items", "idx_cost_line_items_compartment", "CREATE INDEX IF NOT EXISTS idx_cost_line_items_compartment ON cost_line_items(compartment_id)"),
            ("cost_line_items", "idx_cost_line_items_resource", "CREATE INDEX IF NOT EXISTS idx_cost_line_items_resource ON cost_line_items(resource_id)"),
        ]
        with engine.begin() as conn:
            for table_name, _idx, stmt in index_specs:
                if table_name in tables:
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        # Keep startup resilient if optional columns/indexes are unavailable.
                        continue
    except Exception:
        pass


def _ensure_phase3_schema() -> None:
    """Ensure Phase 3 aggregate/snapshot/job schema exists for brownfield DBs."""
    if "sqlite" not in settings.database_url:
        return
    try:
        with engine.begin() as conn:
            # Ensure new snapshot columns exist on legacy table.
            try:
                cols = {c["name"] for c in inspect(engine).get_columns("cost_snapshots")}
            except Exception:
                cols = set()
            if "cost_snapshots" in set(inspect(engine).get_table_names()):
                if "snapshot_uuid" not in cols:
                    conn.execute(text("ALTER TABLE cost_snapshots ADD COLUMN snapshot_uuid VARCHAR(36)"))
                if "name" not in cols:
                    conn.execute(text("ALTER TABLE cost_snapshots ADD COLUMN name VARCHAR(128)"))
                if "scope" not in cols:
                    conn.execute(text("ALTER TABLE cost_snapshots ADD COLUMN scope JSON"))
                if "data" not in cols:
                    conn.execute(text("ALTER TABLE cost_snapshots ADD COLUMN data JSON"))
                if "computed_at" not in cols:
                    conn.execute(text("ALTER TABLE cost_snapshots ADD COLUMN computed_at DATETIME"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cost_snapshots_snapshot_uuid ON cost_snapshots(snapshot_uuid)"))

            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS daily_cost_by_service (
                        date DATE NOT NULL,
                        service VARCHAR(128) NOT NULL,
                        cost NUMERIC(18,6) NOT NULL DEFAULT 0,
                        currency VARCHAR(16) NOT NULL DEFAULT 'USD',
                        PRIMARY KEY (date, service)
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_daily_cost_by_service_date_service ON daily_cost_by_service(date, service)"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS monthly_cost_by_service (
                        month DATE NOT NULL,
                        service VARCHAR(128) NOT NULL,
                        cost NUMERIC(18,6) NOT NULL DEFAULT 0,
                        PRIMARY KEY (month, service)
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_monthly_cost_by_service_month_service ON monthly_cost_by_service(month, service)"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS cost_by_compartment (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        compartment_ocid VARCHAR(255),
                        compartment_name VARCHAR(255),
                        service VARCHAR(128),
                        cost NUMERIC(18,6) NOT NULL DEFAULT 0
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cost_by_compartment_date_compartment ON cost_by_compartment(date, compartment_ocid)"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS cost_by_resource (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        resource_ocid VARCHAR(255) NOT NULL,
                        resource_name VARCHAR(255),
                        service VARCHAR(128),
                        compartment_ocid VARCHAR(255),
                        cost NUMERIC(18,6) NOT NULL DEFAULT 0
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cost_by_resource_resource_ocid ON cost_by_resource(resource_ocid)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cost_by_resource_date_resource ON cost_by_resource(date, resource_ocid)"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS license_cost_table (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        license_type VARCHAR(64) NOT NULL,
                        sku VARCHAR(255),
                        cost NUMERIC(18,6) NOT NULL DEFAULT 0
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_license_cost_table_date_license_type ON license_cost_table(date, license_type)"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS storage_waste_table (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        waste_type VARCHAR(64) NOT NULL,
                        resource_ocid VARCHAR(255),
                        cost NUMERIC(18,6) NOT NULL DEFAULT 0,
                        details JSON
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_storage_waste_table_date_waste_type ON storage_waste_table(date, waste_type)"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS job_runs (
                        id VARCHAR(36) PRIMARY KEY,
                        job_type VARCHAR(64) NOT NULL,
                        status VARCHAR(32) NOT NULL DEFAULT 'queued',
                        progress INTEGER NOT NULL DEFAULT 0,
                        params JSON,
                        result JSON,
                        error_message TEXT,
                        created_at DATETIME,
                        started_at DATETIME,
                        finished_at DATETIME
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_job_runs_job_type ON job_runs(job_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_job_runs_status ON job_runs(status)"))
    except Exception:
        pass


def _ensure_phase4_schema() -> None:
    """Ensure Phase 4 diagnostics schema exists for brownfield DBs."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS oci_diagnostics (
                        id VARCHAR(36) PRIMARY KEY,
                        status VARCHAR(32) NOT NULL DEFAULT 'degraded',
                        config_detected BOOLEAN NOT NULL DEFAULT 0,
                        key_readable BOOLEAN NOT NULL DEFAULT 0,
                        tenancy_reachable BOOLEAN NOT NULL DEFAULT 0,
                        identity_api_reachable BOOLEAN NOT NULL DEFAULT 0,
                        usage_api_reachable BOOLEAN NOT NULL DEFAULT 0,
                        cost_api_reachable BOOLEAN NOT NULL DEFAULT 0,
                        regions JSON,
                        tenancy_ocid VARCHAR(255),
                        user_ocid VARCHAR(255),
                        fingerprint VARCHAR(128),
                        last_sync_time DATETIME,
                        checked_at DATETIME,
                        message TEXT,
                        error JSON,
                        correlation_id VARCHAR(128)
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_oci_diagnostics_checked_at_desc ON oci_diagnostics(checked_at)"))
    except Exception:
        pass


def _ensure_phase5_schema() -> None:
    """Ensure Phase 5 logging/audit schema exists for brownfield DBs."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS log_events (
                        id VARCHAR(36) PRIMARY KEY,
                        ts DATETIME NOT NULL,
                        level VARCHAR(16) NOT NULL,
                        log_type VARCHAR(32) NOT NULL,
                        source VARCHAR(64) NOT NULL,
                        actor VARCHAR(255),
                        route VARCHAR(512),
                        method VARCHAR(16),
                        status_code INTEGER,
                        correlation_id VARCHAR(128) NOT NULL,
                        request_id VARCHAR(128),
                        job_id VARCHAR(36),
                        resource_ocid VARCHAR(255),
                        compartment_ocid VARCHAR(255),
                        service VARCHAR(128),
                        message TEXT NOT NULL,
                        details JSON
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_log_events_ts_desc ON log_events(ts)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_log_events_type_ts ON log_events(log_type, ts)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_log_events_correlation_id ON log_events(correlation_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_log_events_job_id ON log_events(job_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_log_events_level_ts ON log_events(level, ts)"))

            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id VARCHAR(36) PRIMARY KEY,
                        ts DATETIME NOT NULL,
                        actor VARCHAR(255) NOT NULL,
                        action VARCHAR(64) NOT NULL,
                        target VARCHAR(255),
                        correlation_id VARCHAR(128) NOT NULL,
                        meta JSON
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_events_ts_desc ON audit_events(ts)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_events_actor_ts ON audit_events(actor, ts)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_events_action_ts ON audit_events(action, ts)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_events_correlation_id ON audit_events(correlation_id)"))
    except Exception:
        pass
