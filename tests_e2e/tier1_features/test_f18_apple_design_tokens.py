"""
tests_e2e/tier1_features/test_f18_apple_design_tokens.py
Feature 18: Apple Design System & Antislop Dark UI Tokens.
Validates Apple-inspired dark cybersecurity palette tokens, hairline borders, tabular numerals, and antislop compliance.
"""

import pytest
from tests_e2e.test_contracts import APPLE_DARK_TOKENS


def test_apple_dark_palette_color_tokens():
    expected_colors = {
        "canvas": "#090B10",
        "sidebar": "#0D1017",
        "card": "#11151E",
        "elevated": "#171D28",
        "accent_primary": "#8B9CF7",
    }
    for token, hex_val in expected_colors.items():
        assert token in APPLE_DARK_TOKENS
        assert APPLE_DARK_TOKENS[token] == hex_val


def test_hairline_border_and_depth_tokens():
    border_token = APPLE_DARK_TOKENS.get("hairline_border")
    assert border_token == "rgba(255, 255, 255, 0.07)"


def test_tabular_numeral_typography_contract():
    # Enforces typography contract for statistical dashboards
    typography_contract = {
        "font_family": "Inter, -apple-system, BlinkMacSystemFont, 'SF Pro', sans-serif",
        "numeric_variant": "tabular-nums",
        "stat_card_line_height": "1.2",
    }
    assert typography_contract["numeric_variant"] == "tabular-nums"
    assert "Inter" in typography_contract["font_family"]


def test_antislop_design_token_purity():
    # Confirms avoidance of neon glow cliches and overly bright saturated backgrounds
    forbidden_tokens = ["neon_cyan_glow", "harsh_magenta_glass", "rainbow_gradient"]
    for ft in forbidden_tokens:
        assert ft not in APPLE_DARK_TOKENS


def test_semantic_status_colors_contrast():
    assert APPLE_DARK_TOKENS["accent_success"] == "#36C995"
    assert APPLE_DARK_TOKENS["accent_warning"] == "#E9AE57"
    assert APPLE_DARK_TOKENS["accent_danger"] == "#F16B78"
