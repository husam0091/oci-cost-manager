from services.notifications import build_notification_payload, send_notifications


def test_notification_payload_contract_stability():
    payload = build_notification_payload(
        {
            "alert_id": 123,
            "budget_name": "Core Budget",
            "scope": {"scope_type": "team", "scope_value": "platform"},
            "threshold_crossed": 90,
            "current_spend": 1200.5,
            "projected_spend": 1500.75,
            "days_remaining": 6,
            "reason": "Threshold crossed",
            "suggested_next_step": "/costs",
        }
    )
    assert set(payload.keys()) == {
        "alert_id",
        "budget_name",
        "scope",
        "threshold_crossed",
        "current_spend",
        "projected_spend",
        "days_remaining",
        "reason",
        "suggested_next_step",
    }
    assert payload["scope"] == {"scope_type": "team", "scope_value": "platform"}


def test_notification_webhook_dry_run_only_sends_once_per_call():
    result = send_notifications(
        payload={"budget_name": "Core Budget"},
        email_cfg={"enabled": False},
        webhook_cfg={"enabled": True, "url": "https://example.test/hook", "dry_run": True},
    )
    assert result["webhook"]["sent"] is True
    assert result["webhook"]["error"] is None
    assert result["email"]["sent"] is False
