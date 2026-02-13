"""Allocation and ownership rules engine."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from core.models import AllocationRule, Resource


@dataclass
class AllocationResult:
    env: str
    team: str
    app: str
    allocation_confidence: str
    allocation_reason: str


def ensure_allocation_rules_table(db: Session) -> None:
    """Legacy-safe creation for DBs that predate allocation rules."""
    try:
        if db.bind is not None and db.bind.dialect.name != "sqlite":
            return
    except Exception:
        pass
    db.execute(
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
    db.commit()


def load_enabled_rules(db: Session) -> list[AllocationRule]:
    """Load enabled allocation rules with deterministic ordering."""
    try:
        return (
            db.query(AllocationRule)
            .filter(AllocationRule.is_enabled.is_(True))
            .order_by(AllocationRule.priority.asc(), AllocationRule.id.asc())
            .all()
        )
    except OperationalError:
        ensure_allocation_rules_table(db)
        return []


def _tags(details: dict[str, Any]) -> dict[str, Any]:
    details = details or {}
    out: dict[str, Any] = {}
    defined = details.get("defined_tags") or {}
    freeform = details.get("freeform_tags") or {}
    if isinstance(defined, dict):
        out.update(defined)
    if isinstance(freeform, dict):
        out.update(freeform)
    return out


def _tag_value(tags: dict[str, Any], details: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = tags.get(key)
        if value:
            return str(value)
    for key in keys:
        value = details.get(key)
        if value:
            return str(value)
    return None


def _safe_search(pattern: str, value: str) -> bool:
    try:
        return re.search(pattern, value or "", flags=re.IGNORECASE) is not None
    except re.error:
        return False


def _rule_matches(
    rule: AllocationRule,
    resource: Resource | None,
    compartment_name: str | None,
    sku_text: str,
    image_name: str,
) -> bool:
    expression = (rule.match_expression or "").strip()
    if not expression:
        return False
    rname = resource.name if resource and resource.name else ""
    cid = resource.compartment_id if resource and resource.compartment_id else ""
    details = resource.details if resource and resource.details else {}
    tags = _tags(details)

    if rule.match_type == "resource_name":
        return _safe_search(expression, rname)
    if rule.match_type == "compartment":
        return _safe_search(expression, f"{compartment_name or ''} {cid}")
    if rule.match_type == "sku":
        return _safe_search(expression, sku_text or "")
    if rule.match_type == "image_name":
        return _safe_search(expression, image_name or "")
    if rule.match_type == "tag":
        if "=" in expression:
            key, pattern = expression.split("=", 1)
            key = key.strip()
            value = str(tags.get(key) or details.get(key) or "")
            return _safe_search(pattern.strip(), value)
        return _safe_search(expression, " ".join(f"{k}={v}" for k, v in tags.items()))
    return False


def evaluate_allocation(
    resource: Resource | None,
    rules: Iterable[AllocationRule],
    *,
    compartment_name: str | None = None,
    sku_text: str = "",
) -> AllocationResult:
    details = resource.details if resource and resource.details else {}
    tags = _tags(details)
    image_name = str(details.get("image_name") or "")

    tag_env = _tag_value(tags, details, "environment", "env")
    tag_team = _tag_value(tags, details, "owner_team", "team")
    tag_app = _tag_value(tags, details, "application", "app")

    if tag_env and tag_team and tag_app:
        return AllocationResult(
            env=tag_env,
            team=tag_team,
            app=tag_app,
            allocation_confidence="high",
            allocation_reason="tag_keys_env_team_app",
        )

    env = tag_env
    team = tag_team
    app = tag_app
    matched_rule = None
    for rule in sorted([r for r in rules if r.is_enabled], key=lambda r: (r.priority, r.id)):
        if _rule_matches(rule, resource, compartment_name, sku_text, image_name):
            matched_rule = rule
            env = env or (rule.set_env or None)
            team = team or (rule.set_team or None)
            app = app or (rule.set_app or None)
            if env and team and app:
                break

    if env and team and app and matched_rule:
        return AllocationResult(
            env=env,
            team=team,
            app=app,
            allocation_confidence="medium",
            allocation_reason=f"rule:{matched_rule.id}:{matched_rule.name}",
        )
    if env and team and app:
        return AllocationResult(
            env=env,
            team=team,
            app=app,
            allocation_confidence="medium",
            allocation_reason="partial_tag_completion",
        )

    return AllocationResult(
        env=env or "Unallocated",
        team=team or "Unallocated",
        app=app or "Unallocated",
        allocation_confidence="low",
        allocation_reason=(f"rule_partial:{matched_rule.id}" if matched_rule else "no_match"),
    )
