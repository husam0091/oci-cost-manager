"""Notification adapters for budget alerts."""

from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from typing import Any
from urllib import request as urlrequest

from core.secrets import resolve_secret


def _email_enabled(cfg: dict[str, Any]) -> bool:
    return bool(cfg.get("enabled") and cfg.get("smtp_host") and cfg.get("email_from") and cfg.get("email_to"))


def _webhook_enabled(cfg: dict[str, Any]) -> bool:
    return bool(cfg.get("enabled") and cfg.get("url"))


def build_notification_payload(alert_event: dict[str, Any]) -> dict[str, Any]:
    return {
        "alert_id": alert_event.get("alert_id"),
        "budget_name": alert_event.get("budget_name"),
        "scope": alert_event.get("scope"),
        "threshold_crossed": alert_event.get("threshold_crossed"),
        "current_spend": alert_event.get("current_spend"),
        "projected_spend": alert_event.get("projected_spend"),
        "days_remaining": alert_event.get("days_remaining"),
        "reason": alert_event.get("reason"),
        "suggested_next_step": alert_event.get("suggested_next_step"),
    }


def send_notifications(
    *,
    payload: dict[str, Any],
    email_cfg: dict[str, Any],
    webhook_cfg: dict[str, Any],
) -> dict[str, Any]:
    results = {"email": {"sent": False, "error": None}, "webhook": {"sent": False, "error": None}}

    if _email_enabled(email_cfg):
        try:
            msg = EmailMessage()
            msg["Subject"] = f"[OCI Cost Manager] Budget Alert: {payload.get('budget_name')}"
            msg["From"] = email_cfg.get("email_from")
            recipients = email_cfg.get("email_to") or []
            msg["To"] = ", ".join(recipients)
            msg.set_content(json.dumps(payload, indent=2))
            with smtplib.SMTP(email_cfg["smtp_host"], int(email_cfg.get("smtp_port") or 587), timeout=10) as server:
                server.starttls()
                if email_cfg.get("smtp_username"):
                    smtp_password = resolve_secret(email_cfg.get("smtp_password"), env_var="SMTP_PASSWORD") or ""
                    server.login(email_cfg.get("smtp_username"), smtp_password)
                server.send_message(msg)
            results["email"]["sent"] = True
        except Exception as exc:
            results["email"]["error"] = str(exc)

    if _webhook_enabled(webhook_cfg):
        if webhook_cfg.get("dry_run"):
            results["webhook"]["sent"] = True
        else:
            try:
                body = json.dumps(
                    {
                        "text": f"Budget alert: {payload.get('budget_name')}",
                        "payload": payload,
                    }
                ).encode("utf-8")
                req = urlrequest.Request(
                    webhook_cfg["url"],
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlrequest.urlopen(req, timeout=10) as resp:
                    if 200 <= int(getattr(resp, "status", 200)) < 300:
                        results["webhook"]["sent"] = True
                    else:
                        results["webhook"]["error"] = f"HTTP {getattr(resp, 'status', 'unknown')}"
            except Exception as exc:
                results["webhook"]["error"] = str(exc)

    return results
