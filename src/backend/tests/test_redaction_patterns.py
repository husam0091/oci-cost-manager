from services.event_logger import redact_sensitive


def test_redacts_pem_blocks():
    text = "x -----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY----- y"
    redacted = redact_sensitive(text)
    assert "[REDACTED_SECRET]" in redacted
    assert "PRIVATE KEY-----\nabc" not in redacted


def test_redacts_bearer_tokens_and_password_fields():
    payload = {
        "Authorization": "Bearer abcdefghijklmnopqrstuvwxyz0123456789",
        "password": "my-password",
        "nested": {"api_token": "tok_abcdefghijklmnopqrstuvwxyz012345"},
    }
    redacted = redact_sensitive(payload)
    assert redacted["password"] == "[REDACTED_SECRET]"
    assert redacted["nested"]["api_token"] == "[REDACTED_SECRET]"
    assert "[REDACTED_SECRET]" in redacted["Authorization"]


def test_redacts_high_entropy_strings():
    token = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0U1v2W3x4Y5z6"
    redacted = redact_sensitive({"value": token})
    assert redacted["value"] == "[REDACTED_SECRET]"

