"""
PrivShield Data Masking Engine
Implements specialized, customizable masking and tokenization algorithms across
financial, healthcare, government, HR, and generic identifiers.
Preserves trailing or boundary digits while eliminating raw PII.
Exports apply_masking (for pandas Series) and apply_masking_rule (for scalar values).
"""

import hashlib
import hmac
import re
import string
from typing import Any, Optional
import pandas as pd


def mask_email(val: Any) -> str:
    """Mask email preserving first character, character before @, and domain."""
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if "@" not in s:
        return mask_full(s)

    parts = s.split("@", 1)
    local = parts[0]
    domain = parts[1]

    if not local:
        return mask_full(s)

    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + ("*" * (len(local) - 2)) + local[-1]

    return f"{masked_local}@{domain}"


def mask_phone(val: Any) -> str:
    """
    Mask phone number preserving network prefix and trailing 3 digits.
    Example: '+962 78 501 9283' -> '+962 78****283' or '079****567'.
    """
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    digits = re.sub(r"\D", "", s)
    if len(digits) < 7:
        return mask_full(s)

    suffix = digits[-3:]
    if s.startswith("+962") or digits.startswith("962"):
        jordan_digits = digits[3:] if digits.startswith("962") else digits
        network_code = jordan_digits[:2] if len(jordan_digits) >= 2 else "79"
        prefix = "+962 " + network_code if " " in s else f"+962{network_code}"
        return f"{prefix}****{suffix}"
    elif digits.startswith("07"):
        prefix = digits[:3]
        return f"{prefix}****{suffix}"
    elif digits.startswith("7") and len(digits) == 9:
        prefix = f"0{digits[:2]}"
        return f"{prefix}****{suffix}"
    else:
        prefix = digits[:3]
        return f"{prefix}****{suffix}"


def mask_national_id(val: Any) -> str:
    """
    Mask 10-digit Jordanian National ID or generic National ID.
    Preserves birth cohort prefix (first 2 digits) and trailing 4 digits.
    Example: '9981021234' -> '99****1234'.
    """
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    digits = re.sub(r"\D", "", s)
    if len(digits) != 10:
        return mask_partial(s, preserve_prefix=2, preserve_suffix=2)
    return f"{digits[:2]}****{digits[-4:]}"


def mask_ssn(val: Any) -> str:
    """
    Mask US SSN (9 digits), preserving trailing 4 digits: '***-**-1234'.
    """
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    digits = re.sub(r"\D", "", s)
    if len(digits) < 4:
        return mask_full(s)
    suffix = digits[-4:]
    return f"***-**-{suffix}"


def mask_passport(val: Any) -> str:
    """
    Mask passport preserving first 2 letters and trailing 2 characters: 'AB*****89'.
    """
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if len(s) < 5:
        return mask_full(s)
    return mask_partial(s, preserve_prefix=2, preserve_suffix=2)


def mask_iban(val: Any) -> str:
    """
    Mask Jordanian IBAN (30 chars) or global IBAN.
    Preserves country code, check digits (first 4 chars) and trailing 4 digits.
    Example: 'JO94ARAB00000000000012345678' -> 'JO94**********************5678'.
    """
    if val is None or pd.isna(val):
        return ""
    clean = re.sub(r"\s+", "", str(val).strip()).upper()
    if len(clean) < 10:
        return mask_full(clean)
    prefix = clean[:4]
    suffix = clean[-4:]
    mask_length = len(clean) - len(prefix) - len(suffix)
    return f"{prefix}{'*' * mask_length}{suffix}"


def mask_card_number(val: Any, format_style: str = "dots") -> str:
    """
    Mask payment card number preserving trailing 4 digits.
    format_style='dots': '•••• •••• •••• 1234'
    format_style='bin': '4123 **** **** 1234'
    """
    if val is None or pd.isna(val):
        return ""
    digits = re.sub(r"\D", "", str(val).strip())
    if len(digits) < 8:
        return mask_full(str(val))

    suffix = digits[-4:]
    if format_style == "bin" and len(digits) >= 12:
        prefix = digits[:4]
        return f"{prefix} **** **** {suffix}"
    return f"•••• •••• •••• {suffix}"


def mask_ip_address(val: Any, mode: str = "host_mask") -> str:
    """
    Mask IPv4 / IPv6 address:
    mode='host_mask': '192.168.1.142' -> '192.168.***.***'
    mode='cidr': '192.168.1.142' -> '192.168.1.0/24'
    """
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if "." in s:
        parts = s.split(".")
        if len(parts) == 4:
            if mode == "cidr":
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
            return f"{parts[0]}.{parts[1]}.***.***"
    return "[IP REDACTED]"


def mask_address(val: Any) -> str:
    """
    Mask residential or street address, preserving city/region if comma-delimited.
    """
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        return f"*** {parts[-1]}"
    return "*** Location"


def mask_full(val: Any, placeholder: str = "[REDACTED]") -> str:
    """Completely redact a value."""
    if val is None or pd.isna(val):
        return ""
    return placeholder


def mask_partial(val: Any, preserve_prefix: int = 2, preserve_suffix: int = 4, mask_char: str = "*") -> str:
    """Generic partial masking preserving prefix and suffix lengths."""
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if len(s) <= (preserve_prefix + preserve_suffix):
        return mask_char * len(s)
    prefix = s[:preserve_prefix]
    suffix = s[-preserve_suffix:] if preserve_suffix > 0 else ""
    return f"{prefix}{mask_char * (len(s) - preserve_prefix - preserve_suffix)}{suffix}"


def mask_hash(val: Any, salt: str = "FinGuard_Salt_2026") -> str:
    """Deterministic salted SHA-256 pseudonymization."""
    if val is None or pd.isna(val):
        return ""
    h = hashlib.sha256(f"{salt}_{val}".encode("utf-8")).hexdigest()
    return f"HASH-{h[:12].upper()}"


def mask_salted_token(val: Any, salt: str = "PrivShield_Salt_2026", prefix: str = "TOK") -> str:
    """Cryptographic salted HMAC token for pseudonymization."""
    if val is None or pd.isna(val):
        return ""
    h = hmac.new(salt.encode("utf-8"), str(val).encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{prefix}-{h[:12].upper()}"


def tokenize_format_preserving(val: Any, salt: str = "FPT_Salt_2026") -> str:
    """
    Format-Preserving Tokenization (FPT):
    Substitutes digits with deterministic pseudo-digits and letters with pseudo-letters,
    preserving string length, punctuation, hyphens, and whitespace.
    """
    if val is None or pd.isna(val):
        return ""
    s = str(val)
    # Derive deterministic keystream per value
    seed_hash = hashlib.sha256(f"{salt}_{s}".encode("utf-8")).digest()
    result = []
    for idx, char in enumerate(s):
        key_byte = seed_hash[idx % len(seed_hash)]
        if char.isdigit():
            new_digit = str((int(char) + key_byte) % 10)
            result.append(new_digit)
        elif char.isupper():
            new_char = chr(ord('A') + (ord(char) - ord('A') + key_byte) % 26)
            result.append(new_char)
        elif char.islower():
            new_char = chr(ord('a') + (ord(char) - ord('a') + key_byte) % 26)
            result.append(new_char)
        else:
            result.append(char)
    return "".join(result)


def apply_masking_rule(val: Any, rule_name: str) -> str:
    """Dispatch masking based on rule name or specific identifier type."""
    r = rule_name.lower().strip()
    if r in ("email", "mask_email"):
        return mask_email(val)
    if r in ("phone", "phone_number", "mask_phone"):
        return mask_phone(val)
    if r in ("national_id", "mask_national_id", "c_nat_ident"):
        return mask_national_id(val)
    if r in ("ssn", "mask_ssn"):
        return mask_ssn(val)
    if r in ("passport", "mask_passport"):
        return mask_passport(val)
    if r in ("ip", "ip_address", "mask_ip"):
        return mask_ip_address(val)
    if r in ("address", "mask_address"):
        return mask_address(val)
    if r in ("iban", "mask_iban", "x_iban_code"):
        return mask_iban(val)
    if r in ("card_number", "mask_card", "card"):
        return mask_card_number(val, format_style="bin")
    if r in ("card_dots", "dots"):
        return mask_card_number(val, format_style="dots")
    if r in ("redact", "redact_full", "full_redaction", "mask_full"):
        return mask_full(val)
    if r in ("hash", "sha256", "mask_hash"):
        return mask_hash(val)
    if r in ("token", "salted_token", "pseudonym", "mask_token"):
        return mask_salted_token(val)
    if r in ("fpt", "format_preserving"):
        return tokenize_format_preserving(val)
    if r in ("partial", "mask_partial"):
        return mask_partial(val)
    return mask_partial(val)


def apply_masking(series: pd.Series, rule: str) -> pd.Series:
    """Applies a masking rule to all elements in a pandas Series."""
    return series.apply(lambda v: apply_masking_rule(v, rule))
