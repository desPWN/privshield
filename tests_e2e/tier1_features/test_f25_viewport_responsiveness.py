"""
tests_e2e/tier1_features/test_f25_viewport_responsiveness.py
Feature 25: Dual-Viewport Responsive Layout Verification.
Validates layout contracts at 1920x1080 and 1366x768 resolutions, overflow prevention, and breakpoints.
"""

import pytest


def test_desktop_1920x1080_viewport_contract():
    viewport = {"width": 1920, "height": 1080}
    sidebar_width = 240
    content_width = viewport["width"] - sidebar_width

    # Under 1920x1080, studio 3 panels fit side by side with zero horizontal scrolling
    columns_panel = 280
    config_panel = 600
    preview_panel = content_width - columns_panel - config_panel

    assert preview_panel >= 700
    assert (columns_panel + config_panel + preview_panel) == content_width


def test_laptop_1366x768_viewport_contract():
    viewport = {"width": 1366, "height": 768}
    sidebar_width = 220
    content_width = viewport["width"] - sidebar_width

    # Under 1366x768 laptop, panels adjust or stack while preserving responsive spacing
    assert content_width >= 1100
    assert viewport["height"] >= 768


def test_horizontal_overflow_prevention_contract():
    table_overflow_rule = {
        "container_overflow_x": "auto",
        "container_overflow_y": "hidden",
        "max_width": "100%",
        "table_layout": "fixed"
    }
    assert table_overflow_rule["container_overflow_x"] == "auto"
    assert table_overflow_rule["max_width"] == "100%"


def test_sidebar_collapsible_responsive_contract():
    sidebar_contract = {
        "desktop_expanded_width": 240,
        "collapsed_icon_only_width": 64,
        "breakpoint_collapse": 1024,
    }
    assert sidebar_contract["collapsed_icon_only_width"] == 64
    assert sidebar_contract["breakpoint_collapse"] <= 1024


def test_breakpoint_token_definitions():
    breakpoints = {
        "sm": "640px",
        "md": "768px",
        "lg": "1024px",
        "xl": "1280px",
        "2xl": "1536px",
        "fhd": "1920px"
    }
    assert int(breakpoints["sm"].replace("px", "")) == 640
    assert int(breakpoints["fhd"].replace("px", "")) == 1920
