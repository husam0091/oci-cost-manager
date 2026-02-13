"""Budget evaluation and non-noisy alerting engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from core.models import Budget, BudgetAlertEvent, BudgetDailySnapshot, Compartment, Resource, Setting
from services.notifications import build_notification_payload, send_notifications
from services import get_cost_calculator
from services.allocation import evaluate_allocation, load_enabled_rules

ALERT_COOLDOWN_HOURS = 24


@dataclass
class BudgetStatusEval:
    budget_id: str
    budget_name: str
    scope_type: str
    scope_value: str
    current_spend: float
    budget_limit: float
    utilization_pct: float
    forecast_end_of_month: float
    breach_level: str
    days_remaining: int
    explanation: str
    latest_threshold_crossed: Optional[int]
    narrative: str


def _safe_pct(value: float, base: float) -> float:
    return (value / base * 100.0) if base else 0.0


def ensure_budget_tables(db: Session) -> None:
    try:
        if db.bind is not None and db.bind.dialect.name != "sqlite":
            return
    except Exception:
        pass
    db.execute(
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
    db.execute(
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
    db.execute(
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
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_alert_budget ON budget_alert_events(budget_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_alert_period ON budget_alert_events(period_key)"))
    db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_budget_alert_dedupe_idx ON budget_alert_events(budget_id, period_key, alert_kind, threshold)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_snapshot_budget ON budget_daily_snapshots(budget_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_snapshot_date ON budget_daily_snapshots(snapshot_date)"))
    db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_budget_snapshot_daily_idx ON budget_daily_snapshots(budget_id, snapshot_date)"))
    try:
        cols = {c["name"] for c in inspect(db.bind).get_columns("budgets")}  # type: ignore[arg-type]
        if "notifications_enabled" not in cols:
            db.execute(text("ALTER TABLE budgets ADD COLUMN notifications_enabled BOOLEAN DEFAULT 0"))
    except Exception:
        pass
    db.commit()


def _ensure_setting_notification_columns(db: Session) -> None:
    """Best-effort patch for legacy DBs missing notification columns on settings."""
    columns = [
        ("notifications_email_enabled", "BOOLEAN DEFAULT 0"),
        ("notifications_smtp_host", "VARCHAR(255)"),
        ("notifications_smtp_port", "INTEGER DEFAULT 587"),
        ("notifications_smtp_username", "VARCHAR(255)"),
        ("notifications_smtp_password", "VARCHAR(512)"),
        ("notifications_email_from", "VARCHAR(255)"),
        ("notifications_email_to", "JSON"),
        ("notifications_webhook_enabled", "BOOLEAN DEFAULT 0"),
        ("notifications_webhook_url", "VARCHAR(1024)"),
        ("notifications_webhook_dry_run", "BOOLEAN DEFAULT 1"),
    ]
    try:
        existing = {c["name"] for c in inspect(db.bind).get_columns("settings")}  # type: ignore[arg-type]
        for name, sql_type in columns:
            if name not in existing:
                db.execute(text(f"ALTER TABLE settings ADD COLUMN {name} {sql_type}"))
        db.commit()
    except Exception:
        db.rollback()


def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _next_month_start(dt: datetime) -> datetime:
    if dt.month == 12:
        return dt.replace(year=dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(month=dt.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


def _descendants(selected_ids: set[str], compartments: list[Compartment]) -> set[str]:
    children: dict[str, list[str]] = {}
    for comp in compartments:
        if comp.parent_id:
            children.setdefault(comp.parent_id, []).append(comp.id)
    out = set(selected_ids)
    stack = list(selected_ids)
    while stack:
        parent = stack.pop()
        for child in children.get(parent, []):
            if child not in out:
                out.add(child)
                stack.append(child)
    return out


def _budget_scope_match(
    budget: Budget,
    *,
    row: dict,
    resource: Optional[Resource],
    alloc_env: str,
    alloc_team: str,
    alloc_app: str,
    compartment_scope: set[str],
) -> bool:
    if budget.scope_type == "global":
        return True
    if budget.scope_type == "compartment":
        comp_id = resource.compartment_id if resource else row.get("compartment_id")
        return comp_id in compartment_scope
    if budget.scope_type == "team":
        return alloc_team == budget.scope_value
    if budget.scope_type == "app":
        return alloc_app == budget.scope_value
    if budget.scope_type == "env":
        return alloc_env == budget.scope_value
    return False


def _explanation(utilization: float, forecast: float, limit_amount: float, breach_level: str) -> str:
    if breach_level == "critical":
        if utilization >= 100.0:
            return "Actual spend has exceeded budget limit."
        return "Forecast indicates end-of-month budget breach."
    if breach_level == "warning":
        return "Budget utilization is approaching limit."
    return "Budget is healthy for current period."


def _evaluate_threshold_crossing(status: BudgetStatusEval, thresholds: list[int]) -> Optional[int]:
    util = status.utilization_pct
    hit = [t for t in sorted(set(int(x) for x in thresholds)) if util >= t]
    return hit[-1] if hit else None


def _emit_alert_if_needed(
    db: Session,
    *,
    budget: Budget,
    status: BudgetStatusEval,
    now_utc: datetime,
    notification_cfg: dict,
) -> None:
    period_key = now_utc.strftime("%Y-%m")
    threshold = status.latest_threshold_crossed
    if threshold is not None:
        existing = (
            db.query(BudgetAlertEvent)
            .filter(
                BudgetAlertEvent.budget_id == budget.budget_id,
                BudgetAlertEvent.period_key == period_key,
                BudgetAlertEvent.alert_kind == "threshold",
                BudgetAlertEvent.threshold == threshold,
            )
            .first()
        )
        if not existing:
            recent = (
                db.query(BudgetAlertEvent)
                .filter(
                    BudgetAlertEvent.budget_id == budget.budget_id,
                    BudgetAlertEvent.alert_kind == "threshold",
                    BudgetAlertEvent.triggered_at >= now_utc - timedelta(hours=ALERT_COOLDOWN_HOURS),
                )
                .first()
            )
            if not recent:
                event = BudgetAlertEvent(
                    budget_id=budget.budget_id,
                    period_key=period_key,
                    alert_kind="threshold",
                    threshold=threshold,
                    triggered_at=now_utc,
                    payload={
                        "budget_name": budget.name,
                        "scope": {"scope_type": budget.scope_type, "scope_value": budget.scope_value},
                        "threshold_crossed": threshold,
                        "current_spend": status.current_spend,
                        "projected_spend": status.forecast_end_of_month,
                        "days_remaining": status.days_remaining,
                        "reason": status.explanation,
                        "recommended_next_step": "/costs or /recommendations",
                    },
                )
                db.add(event)
                db.flush()
                if budget.notifications_enabled:
                    payload = build_notification_payload(
                        {
                            "alert_id": event.id,
                            "budget_name": budget.name,
                            "scope": {"scope_type": budget.scope_type, "scope_value": budget.scope_value},
                            "threshold_crossed": threshold,
                            "current_spend": status.current_spend,
                            "projected_spend": status.forecast_end_of_month,
                            "days_remaining": status.days_remaining,
                            "reason": status.explanation,
                            "suggested_next_step": "/costs or /recommendations",
                        }
                    )
                    send_notifications(
                        payload=payload,
                        email_cfg=notification_cfg.get("email", {}),
                        webhook_cfg=notification_cfg.get("webhook", {}),
                    )

    forecast_breach = status.forecast_end_of_month >= status.budget_limit
    if forecast_breach:
        existing_forecast = (
            db.query(BudgetAlertEvent)
            .filter(
                BudgetAlertEvent.budget_id == budget.budget_id,
                BudgetAlertEvent.period_key == period_key,
                BudgetAlertEvent.alert_kind == "forecast",
            )
            .first()
        )
        if not existing_forecast:
            recent_forecast = (
                db.query(BudgetAlertEvent)
                .filter(
                    BudgetAlertEvent.budget_id == budget.budget_id,
                    BudgetAlertEvent.alert_kind == "forecast",
                    BudgetAlertEvent.triggered_at >= now_utc - timedelta(hours=ALERT_COOLDOWN_HOURS),
                )
                .first()
            )
            if not recent_forecast:
                event = BudgetAlertEvent(
                    budget_id=budget.budget_id,
                    period_key=period_key,
                    alert_kind="forecast",
                    threshold=None,
                    triggered_at=now_utc,
                    payload={
                        "budget_name": budget.name,
                        "scope": {"scope_type": budget.scope_type, "scope_value": budget.scope_value},
                        "threshold_crossed": None,
                        "current_spend": status.current_spend,
                        "projected_spend": status.forecast_end_of_month,
                        "days_remaining": status.days_remaining,
                        "reason": "Forecast indicates budget breach before month end.",
                        "recommended_next_step": "/costs or /recommendations",
                    },
                )
                db.add(event)
                db.flush()
                if budget.notifications_enabled:
                    payload = build_notification_payload(
                        {
                            "alert_id": event.id,
                            "budget_name": budget.name,
                            "scope": {"scope_type": budget.scope_type, "scope_value": budget.scope_value},
                            "threshold_crossed": None,
                            "current_spend": status.current_spend,
                            "projected_spend": status.forecast_end_of_month,
                            "days_remaining": status.days_remaining,
                            "reason": "Forecast indicates budget breach before month end.",
                            "suggested_next_step": "/costs or /recommendations",
                        }
                    )
                    send_notifications(
                        payload=payload,
                        email_cfg=notification_cfg.get("email", {}),
                        webhook_cfg=notification_cfg.get("webhook", {}),
                    )


def _guess_service_name(sku_names: str, resource_type: str) -> str:
    text = sku_names.lower()
    rtype = (resource_type or "").lower()
    if "sql" in text or "database" in text or "db" in rtype:
        return "Database"
    if "storage" in text or "backup" in text or "snapshot" in text or "volume" in text or "object" in rtype:
        return "Storage"
    if "network" in text or "load balancer" in text:
        return "Network"
    return "Compute"


def _narrative(
    *,
    forecast_eom: float,
    limit_amount: float,
    days_remaining: int,
    current_spend: float,
    service_current: dict[str, float],
    service_previous: dict[str, float],
) -> str:
    over_by = max(forecast_eom - limit_amount, 0.0)
    days_to_breach = int((limit_amount - current_spend) / (current_spend / max((30 - days_remaining), 1))) if current_spend > 0 and forecast_eom > limit_amount else None
    drivers = []
    for name in sorted(service_current.keys(), key=lambda n: service_current.get(n, 0.0), reverse=True):
        cur = float(service_current.get(name, 0.0))
        prev = float(service_previous.get(name, 0.0))
        if cur <= 0:
            continue
        pct = _safe_pct(cur - prev, prev) if prev else 100.0
        if pct > 0:
            drivers.append(f"{name} (+{pct:.0f}%)")
        if len(drivers) == 2:
            break
    driver_text = ", ".join(drivers) if drivers else "No major positive movers detected"
    if forecast_eom > limit_amount:
        lead = f"At current run-rate, this budget is forecast to exceed by ${over_by:.2f}"
        if days_to_breach is not None and days_to_breach >= 0:
            lead += f" in ~{days_to_breach} days."
        else:
            lead += "."
    else:
        lead = "At current run-rate, this budget remains within limit."
    return f"{lead} Primary drivers this month: {driver_text}."


def evaluate_budget_statuses(db: Session, *, persist_alerts: bool = True) -> list[BudgetStatusEval]:
    try:
        budgets = db.query(Budget).order_by(Budget.created_at.asc()).all()
    except OperationalError:
        ensure_budget_tables(db)
        budgets = []
    enabled = [b for b in budgets if b.enabled]
    if not enabled:
        return []

    now_utc = datetime.now(UTC)
    start = _month_start(now_utc)
    end_exclusive = _next_month_start(start)
    previous_start = _month_start(start - timedelta(days=1))
    previous_end = start

    calc = get_cost_calculator()
    current_rows = calc.get_costs_by_resource(start, end_exclusive, include_skus=True)
    previous_rows = calc.get_costs_by_resource(previous_start, previous_end, include_skus=True)

    resource_ids = list(
        {
            *(r.get("resource_id") for r in current_rows if r.get("resource_id")),
            *(r.get("resource_id") for r in previous_rows if r.get("resource_id")),
        }
    )
    resources = db.query(Resource).filter(Resource.ocid.in_(resource_ids)).all() if resource_ids else []
    resources_by_id = {r.ocid: r for r in resources}
    compartments = db.query(Compartment).all()
    rules = load_enabled_rules(db)
    try:
        setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
    except OperationalError:
        _ensure_setting_notification_columns(db)
        try:
            setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
        except OperationalError:
            setting = None
    notification_cfg = {
        "email": {
            "enabled": bool(getattr(setting, "notifications_email_enabled", False)),
            "smtp_host": getattr(setting, "notifications_smtp_host", None),
            "smtp_port": getattr(setting, "notifications_smtp_port", 587),
            "smtp_username": getattr(setting, "notifications_smtp_username", None),
            "smtp_password": getattr(setting, "notifications_smtp_password", None),
            "email_from": getattr(setting, "notifications_email_from", None),
            "email_to": list(getattr(setting, "notifications_email_to", None) or []),
        },
        "webhook": {
            "enabled": bool(getattr(setting, "notifications_webhook_enabled", False)),
            "url": getattr(setting, "notifications_webhook_url", None),
            "dry_run": bool(getattr(setting, "notifications_webhook_dry_run", True)),
        },
    }

    days_elapsed = max((now_utc - start).days + 1, 1)
    days_total = max((end_exclusive - start).days, 1)
    days_remaining = max(days_total - days_elapsed, 0)

    prev_by_budget: dict[str, float] = {b.budget_id: 0.0 for b in enabled}
    current_by_budget: dict[str, float] = {b.budget_id: 0.0 for b in enabled}
    service_current_by_budget: dict[str, dict[str, float]] = {b.budget_id: {} for b in enabled}
    service_prev_by_budget: dict[str, dict[str, float]] = {b.budget_id: {} for b in enabled}
    scope_cache: dict[str, set[str]] = {}

    for budget in enabled:
        if budget.scope_type == "compartment":
            selected = {budget.scope_value}
            scope_cache[budget.budget_id] = _descendants(selected, compartments) if budget.include_children else selected
        else:
            scope_cache[budget.budget_id] = set()

    def _sum_rows(rows: list[dict], out: dict[str, float], service_out: dict[str, dict[str, float]]) -> None:
        for row in rows:
            rid = row.get("resource_id")
            cost = float(row.get("total_cost") or 0.0)
            if cost <= 0:
                continue
            resource = resources_by_id.get(rid)
            compartment_name = row.get("compartment_name") or (resource.compartment_id if resource else None) or "Unknown"
            sku_text = " ".join((s.get("sku_name") or "") for s in (row.get("skus") or []))
            service_name = _guess_service_name(sku_text, resource.type if resource else "")
            allocation = evaluate_allocation(
                resource,
                rules,
                compartment_name=compartment_name,
                sku_text=sku_text,
            )
            for budget in enabled:
                if _budget_scope_match(
                    budget,
                    row=row,
                    resource=resource,
                    alloc_env=allocation.env,
                    alloc_team=allocation.team,
                    alloc_app=allocation.app,
                    compartment_scope=scope_cache.get(budget.budget_id, set()),
                ):
                    out[budget.budget_id] = out.get(budget.budget_id, 0.0) + cost
                    by_service = service_out.setdefault(budget.budget_id, {})
                    by_service[service_name] = by_service.get(service_name, 0.0) + cost

    _sum_rows(current_rows, current_by_budget, service_current_by_budget)
    _sum_rows(previous_rows, prev_by_budget, service_prev_by_budget)

    statuses: list[BudgetStatusEval] = []
    for budget in enabled:
        current_spend = round(current_by_budget.get(budget.budget_id, 0.0), 2)
        prev_spend = round(prev_by_budget.get(budget.budget_id, 0.0), 2)
        utilization = round(_safe_pct(current_spend, budget.limit_amount), 2)
        burn_rate_daily = current_spend / days_elapsed if days_elapsed else 0.0
        forecast_eom = round(burn_rate_daily * days_total, 2)
        growth_pct = _safe_pct(current_spend - prev_spend, prev_spend) if prev_spend else 0.0
        forecast_breach = forecast_eom >= budget.limit_amount

        breach_level = "none"
        if utilization >= 100.0 or forecast_breach:
            breach_level = "critical"
        elif utilization >= 75.0:
            breach_level = "warning"
        if budget.growth_cap_pct is not None and growth_pct > budget.growth_cap_pct:
            breach_level = "critical" if breach_level == "none" else breach_level

        latest_threshold = _evaluate_threshold_crossing(
            BudgetStatusEval(
                budget_id=budget.budget_id,
                budget_name=budget.name,
                scope_type=budget.scope_type,
                scope_value=budget.scope_value,
                current_spend=current_spend,
                budget_limit=round(float(budget.limit_amount), 2),
                utilization_pct=utilization,
                forecast_end_of_month=forecast_eom,
                breach_level=breach_level,
                days_remaining=days_remaining,
                explanation="",
                latest_threshold_crossed=None,
                narrative="",
            ),
            list(budget.alert_thresholds or [50, 75, 90, 100]),
        )
        explanation = _explanation(utilization, forecast_eom, budget.limit_amount, breach_level)
        if budget.growth_cap_pct is not None and growth_pct > budget.growth_cap_pct:
            explanation = f"Monthly growth {growth_pct:.2f}% exceeds cap {budget.growth_cap_pct:.2f}%."
        narrative = _narrative(
            forecast_eom=forecast_eom,
            limit_amount=float(budget.limit_amount),
            days_remaining=days_remaining,
            current_spend=current_spend,
            service_current=service_current_by_budget.get(budget.budget_id, {}),
            service_previous=service_prev_by_budget.get(budget.budget_id, {}),
        )
        status = BudgetStatusEval(
            budget_id=budget.budget_id,
            budget_name=budget.name,
            scope_type=budget.scope_type,
            scope_value=budget.scope_value,
            current_spend=current_spend,
            budget_limit=round(float(budget.limit_amount), 2),
            utilization_pct=utilization,
            forecast_end_of_month=forecast_eom,
            breach_level=breach_level,
            days_remaining=days_remaining,
            explanation=explanation,
            latest_threshold_crossed=latest_threshold,
            narrative=narrative,
        )
        statuses.append(status)
        if persist_alerts:
            _emit_alert_if_needed(db, budget=budget, status=status, now_utc=now_utc, notification_cfg=notification_cfg)
            snapshot_date = now_utc.date().isoformat()
            snap = (
                db.query(BudgetDailySnapshot)
                .filter(BudgetDailySnapshot.budget_id == budget.budget_id, BudgetDailySnapshot.snapshot_date == snapshot_date)
                .one_or_none()
            )
            if not snap:
                snap = BudgetDailySnapshot(
                    budget_id=budget.budget_id,
                    snapshot_date=snapshot_date,
                )
                db.add(snap)
            snap.current_spend = status.current_spend
            snap.utilization_pct = status.utilization_pct
            snap.forecast_end_of_month = status.forecast_end_of_month

    if persist_alerts:
        db.commit()
    return statuses
