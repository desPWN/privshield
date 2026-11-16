"""
Unit tests for FinGuard Data Masking Engine.
Tests all specialized masking functions, edge cases, boundaries, and formats.
"""

from backend.app.engine.masking import (
    apply_masking_rule,
    mask_card_number,
    mask_email,
    mask_full,
    mask_hash,
    mask_iban,
    mask_national_id,
    mask_partial,
    mask_phone,
)


def test_mask_email():
    assert mask_email("jafar.alhashemi@arab-bank.jo") == "j*************i@arab-bank.jo"
    assert mask_email("omar@gmail.com") == "o**r@gmail.com"
    assert mask_email("ab@domain.com") == "a*@domain.com"
    assert mask_email("a@domain.com") == "a*@domain.com"
    assert mask_email(None) == ""
    assert mask_email("invalid-email") == "[REDACTED]"


def test_mask_phone():
    assert mask_phone("0791234567") == "079****567"
    assert mask_phone("+962 78 501 9283") == "+962 78****283"
    assert mask_phone("123") == "[REDACTED]"
    assert mask_phone(None) == ""


def test_mask_national_id():
    assert mask_national_id("9981021234") == "99****1234"
    assert mask_national_id("2001849201") == "20****9201"
    assert mask_national_id(None) == ""


def test_mask_iban():
    iban = "JO94ARAB00000000000012345678"
    masked = mask_iban(iban)
    assert masked.startswith("JO94")
    assert masked.endswith("5678")
    assert len(masked) == len(iban)
    assert "*" in masked
    assert mask_iban(None) == ""


def test_mask_card_number():
    card = "4123 9812 4019 5821"
    dots_masked = mask_card_number(card, format_style="dots")
    assert dots_masked == "•••• •••• •••• 5821"

    bin_masked = mask_card_number(card, format_style="bin")
    assert bin_masked == "4123 **** **** 5821"
    assert mask_card_number(None) == ""


def test_mask_full():
    assert mask_full("Secret Customer") == "[REDACTED]"
    assert mask_full("12345", placeholder="***") == "***"
    assert mask_full(None) == ""


def test_mask_partial():
    assert mask_partial("ABCDEFGH", preserve_prefix=2, preserve_suffix=2) == "AB****GH"
    assert mask_partial("SHORT", preserve_prefix=3, preserve_suffix=3) == "*****"
    assert mask_partial(None) == ""


def test_mask_hash():
    h1 = mask_hash("Customer123", salt="TestSalt")
    h2 = mask_hash("Customer123", salt="TestSalt")
    h3 = mask_hash("Customer999", salt="TestSalt")
    assert h1.startswith("HASH-")
    assert h1 == h2, "Hash must be deterministic for identical salt and value"
    assert h1 != h3, "Different inputs must produce different hashes"
    assert mask_hash(None) == ""


def test_apply_masking_rule_dispatcher():
    assert "@" in apply_masking_rule("test@example.com", "email")
    assert "****" in apply_masking_rule("0791234567", "phone")
    assert "****" in apply_masking_rule("9981021234", "national_id")
    assert apply_masking_rule("secret", "redact") == "[REDACTED]"
    assert apply_masking_rule("secret", "mask_full") == "[REDACTED]"
    assert apply_masking_rule("val", "hash").startswith("HASH-")
    assert apply_masking_rule("val", "mask_hash").startswith("HASH-")
    assert apply_masking_rule("token_me", "token").startswith("TOK-")
    assert apply_masking_rule("token_me", "mask_token").startswith("TOK-")
