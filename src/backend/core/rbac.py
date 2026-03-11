"""RBAC and row-level scope utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from core.auth import get_secret_key
from core.models import Setting, UserAccount


ROLE_JOB_PROFILES = {
    "admin": {
        "title": "Platform Administrator",
        "description": "Owns platform configuration, identity scope, and operational guardrails.",
        "permissions": [
            "Manage integration settings and credentials",
            "Manage SSL certificate settings",
            "Run scans and operational jobs",
            "Create/approve/run all actions",
            "Manage budgets and governance settings",
            "Set role scope boundaries",
        ],
    },
    "finops": {
        "title": "FinOps Analyst",
        "description": "Drives cost optimization within assigned scope with safe operational changes.",
        "permissions": [
            "View all analytics within assigned scope",
            "Create actions and recommendations",
            "Approve/run only safe actions",
            "Manage budgets within scope",
            "Cannot change platform/integration/SSL settings",
        ],
    },
    "engineer": {
        "title": "Engineering Operator",
        "description": "Reviews workload-level optimization opportunities and execution details.",
        "permissions": [
            "View resources/costs/recommendations within assigned scope",
            "Create actions within assigned scope",
            "Cannot approve/run actions",
            "Cannot modify platform settings",
        ],
    },
    "viewer": {
        "title": "Read-only Stakeholder",
        "description": "Consumes reports and operational insights without making changes.",
        "permissions": [
            "Read-only access to dashboards/reports within scope",
            "No action creation or execution",
            "No settings updates",
        ],
    },
}


def role_job_profile(role: str) -> dict[str, Any]:
    key = (role or "viewer").lower()
    return ROLE_JOB_PROFILES.get(key, ROLE_JOB_PROFILES["viewer"])


@dataclass
class Principal:
    username: str
    role: str
    allowed_teams: list[str]
    allowed_apps: list[str]
    allowed_envs: list[str]
    allowed_compartment_ids: list[str]

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, get_secret_key(), algorithms=["HS256"])
    except JWTError:
        return None


def principal_from_user(user: UserAccount) -> Principal:
    return Principal(
        username=user.username,
        role=(user.role or "viewer").lower(),
        allowed_teams=list(user.allowed_teams or []),
        allowed_apps=list(user.allowed_apps or []),
        allowed_envs=list(user.allowed_envs or []),
        allowed_compartment_ids=list(user.allowed_compartment_ids or []),
    )


def principal_from_setting(setting: Optional[Setting]) -> Principal:
    if not setting:
        return Principal(
            username="admin",
            role="admin",
            allowed_teams=[],
            allowed_apps=[],
            allowed_envs=[],
            allowed_compartment_ids=[],
        )
    return Principal(
        username=setting.username or "admin",
        role=(setting.user_role or "admin").lower(),
        allowed_teams=list(setting.allowed_teams or []),
        allowed_apps=list(setting.allowed_apps or []),
        allowed_envs=list(setting.allowed_envs or []),
        allowed_compartment_ids=list(setting.allowed_compartment_ids or []),
    )


def resolve_principal(db: Session, token: Optional[str], *, strict: bool = False) -> Principal:
    try:
        q = db.query(Setting).filter(Setting.id == 1)
        if hasattr(q, "one_or_none"):
            setting = q.one_or_none()
        elif hasattr(q, "first"):
            setting = q.first()
        else:
            setting = None
    except Exception:
        setting = None

    default_principal = principal_from_setting(setting)
    if not token:
        if strict:
            raise PermissionError("Not authenticated")
        return default_principal

    payload = _decode_token(token)
    username = (payload or {}).get("sub")
    if not username:
        if strict:
            raise PermissionError("Invalid token")
        return default_principal

    try:
        user = db.query(UserAccount).filter(UserAccount.username == username, UserAccount.is_active == True).one_or_none()
    except Exception:
        user = None

    if user:
        return principal_from_user(user)

    if setting and username == setting.username:
        return default_principal

    if strict:
        raise PermissionError("User not found or inactive")
    return default_principal


def has_scope_access(
    principal: Principal,
    *,
    team: Optional[str] = None,
    app: Optional[str] = None,
    env: Optional[str] = None,
    compartment_id: Optional[str] = None,
) -> bool:
    if principal.is_admin:
        return True
    if principal.allowed_teams and team and team not in principal.allowed_teams:
        return False
    if principal.allowed_apps and app and app not in principal.allowed_apps:
        return False
    if principal.allowed_envs and env and env not in principal.allowed_envs:
        return False
    if principal.allowed_compartment_ids and compartment_id and compartment_id not in principal.allowed_compartment_ids:
        return False
    return True


def can_create_action(principal: Principal) -> bool:
    return principal.role in {"admin", "finops", "engineer"}


def can_approve_or_run(principal: Principal, risk_level: str) -> bool:
    if principal.role == "admin":
        return True
    if principal.role == "finops":
        return risk_level == "safe"
    return False


def feature_flags(setting: Optional[Setting]) -> dict[str, Any]:
    return {
        "enable_oci_executors": bool(getattr(setting, "enable_oci_executors", False)) if setting else False,
        "enable_destructive_actions": bool(getattr(setting, "enable_destructive_actions", False)) if setting else False,
        "enable_notifications": bool(getattr(setting, "notifications_email_enabled", False) or getattr(setting, "notifications_webhook_enabled", False)) if setting else False,
        "enable_budget_auto_eval": bool(getattr(setting, "enable_budget_auto_eval", True)) if setting else True,
        "enable_demo_mode": bool(getattr(setting, "enable_demo_mode", False)) if setting else False,
    }
