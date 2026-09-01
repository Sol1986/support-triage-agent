from support_triage_agent.guardrails.pii import detect_pii, redact


def test_detects_email() -> None:
    assert "email" in detect_pii("Contact me at jane.doe@example.com please.")


def test_detects_phone_number() -> None:
    assert "phone" in detect_pii("Call me at 415-555-0192 tomorrow.")


def test_detects_card_number() -> None:
    assert "card_number" in detect_pii("My card number is 4111 1111 1111 1111.")


def test_no_pii_in_plain_ticket() -> None:
    assert detect_pii("My package delivery has not arrived.") == []


def test_redact_replaces_email() -> None:
    redacted = redact("Contact me at jane.doe@example.com please.")

    assert "jane.doe@example.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted


def test_redact_leaves_clean_text_unchanged() -> None:
    text = "My package delivery has not arrived."

    assert redact(text) == text
