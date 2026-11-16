"""
FinGuard Zero-PII Logging Filter & Configuration
Redacts sensitive identifiers (IBANs, card numbers, phone numbers, emails, national IDs)
from all application logs.
"""

import logging
import re
from typing import List

PII_LOG_PATTERNS: List[re.Pattern] = [
    # Jordanian IBAN (JO + 2 check digits + 4 bank code + 22 account chars, unspaced, spaced, or hyphenated)
    re.compile(r"(?<![A-Z0-9])JO\d{2}(?:[ -]?[A-Z0-9]{4}){6}[ -]?[A-Z0-9]{2}(?![A-Z0-9])", re.IGNORECASE),
    # International IBAN (2 letters + 2 digits + 11-30 alphanumeric, unspaced, spaced, or hyphenated)
    re.compile(r"(?<![A-Z0-9])[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]{4}){2,7}(?:[ -]?[A-Z0-9]{1,4})?(?![A-Z0-9])", re.IGNORECASE),
    # Jordanian Phone Numbers (Zain 079, Orange 077, Umniah 078 + 7 digits, unspaced, spaced, or hyphenated)
    re.compile(r"(?<!\d)(?:\+962|00962|0)?[\s\-]?7[789](?:[\s\-]?\d){7}(?!\d)"),
    # Standard International Phone (E.164)
    re.compile(r"(?<!\d)\+?[1-9]\d{8,14}(?!\d)"),
    # 10-digit Jordanian National ID
    re.compile(r"(?<!\d)\d{10}(?!\d)"),
    # Email addresses
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    # Formatted Payment Card Numbers (spaced or hyphenated 16-digit cards)
    re.compile(r"\b(?:\d{4}[ -]){3}\d{4}\b"),
    # Payment Card Numbers (Visa, Mastercard, Amex, Discover - continuous PANs)
    re.compile(
        r"(?<!\d)(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})(?!\d)"
    ),
]


class RedactingFilter(logging.Filter):
    """
    Custom logging filter that intercepts log records and redacts any detected PII strings.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)

        redacted = self.redact_text(message)
        record.msg = redacted
        record.args = ()
        return True

    @staticmethod
    def redact_text(text: str) -> str:
        out = text
        for pattern in PII_LOG_PATTERNS:
            out = pattern.sub("[REDACTED_PII]", out)
        return out


def setup_logging(level: int = logging.INFO) -> None:
    """Configures root logger with RedactingFilter and standard stream handler."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Check if redacting filter is already installed
    has_filter = any(isinstance(f, RedactingFilter) for f in root_logger.filters)
    if not has_filter:
        root_logger.addFilter(RedactingFilter())

    # Format handler
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(RedactingFilter())
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            if not any(isinstance(f, RedactingFilter) for f in handler.filters):
                handler.addFilter(RedactingFilter())
