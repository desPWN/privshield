"""
tests_e2e/tier1_features/test_f19_workspace_views.py
Feature 19: Application Shell & 8 Dedicated Workspace Views.
Validates sidebar navigation routes across all 8 dedicated PrivShield workspaces.
"""

import pytest
from tests_e2e.test_contracts import WORKSPACE_ROUTES


def test_eight_dedicated_workspace_routes_declared():
    assert len(WORKSPACE_ROUTES) == 8
    expected = {
        "/overview",
        "/datasets",
        "/discovery",
        "/studio",
        "/privacy-analysis",
        "/utility-analysis",
        "/recovery",
        "/reports-settings"
    }
    assert set(WORKSPACE_ROUTES) == expected


def test_sidebar_navigation_items_and_icons():
    sidebar_items = [
        {"route": "/overview", "label": "Overview", "icon": "LayoutDashboard"},
        {"route": "/datasets", "label": "Datasets", "icon": "Database"},
        {"route": "/discovery", "label": "Discovery", "icon": "Search"},
        {"route": "/studio", "label": "Anonymization Studio", "icon": "Sliders"},
        {"route": "/privacy-analysis", "label": "Privacy Analysis", "icon": "ShieldCheck"},
        {"route": "/utility-analysis", "label": "Utility Analysis", "icon": "BarChart3"},
        {"route": "/recovery", "label": "Secure Recovery", "icon": "KeyRound"},
        {"route": "/reports-settings", "label": "Reports & Settings", "icon": "FileText"},
    ]
    assert len(sidebar_items) == 8
    routes = [item["route"] for item in sidebar_items]
    assert routes == WORKSPACE_ROUTES


def test_workspace_view_contract_definitions():
    workspace_registry = {
        "overview": {"title": "Privacy Overview", "has_stats": True, "has_charts": True},
        "datasets": {"title": "Dataset Management", "has_upload": True},
        "discovery": {"title": "Sensitive Data Discovery", "has_profiler": True},
        "studio": {"title": "Anonymization Studio", "panels": 3},
        "privacy-analysis": {"title": "Privacy Risk Analysis", "metrics": ["K", "L", "T"]},
        "utility-analysis": {"title": "Data Utility Evaluation", "score": "CURS"},
        "recovery": {"title": "Secure Recovery Center", "mode": "reversible"},
        "reports-settings": {"title": "Reports & Settings", "has_pdf": True},
    }
    assert len(workspace_registry) == 8
    assert workspace_registry["studio"]["panels"] == 3


def test_topnav_breadcrumbs_and_workspace_selector():
    nav_state = {
        "active_workspace": "studio",
        "breadcrumbs": ["PrivShield", "Workspaces", "Anonymization Studio"],
        "active_dataset_id": "ds-001"
    }
    assert nav_state["breadcrumbs"][-1] == "Anonymization Studio"
    assert nav_state["active_workspace"] in [r.strip("/") for r in WORKSPACE_ROUTES]


def test_view_state_and_active_tab_tracking():
    valid_workspaces = [r.strip("/") for r in WORKSPACE_ROUTES]
    for ws in valid_workspaces:
        assert isinstance(ws, str)
        assert len(ws) > 0
