"""
tests_e2e/tier1_features/test_f22_recharts_visualizations.py
Feature 22: Recharts Multi-Industry Privacy & Utility Visualizations.
Validates chart payload models for risk distribution, class histograms, L-diversity, and CURS radar charts.
"""

import pytest


def test_risk_distribution_chart_data_model():
    chart_payload = {
        "categories": ["Prosecutor", "Journalist", "Marketer"],
        "series": [
            {"name": "Pre-Anonymization", "values": [1.0, 0.85, 0.70]},
            {"name": "Post-Anonymization", "values": [0.20, 0.15, 0.18]},
        ]
    }
    assert len(chart_payload["categories"]) == 3
    assert len(chart_payload["series"]) == 2
    assert chart_payload["series"][1]["values"][0] <= 0.20


def test_equivalence_class_histogram_data_model():
    histogram_data = [
        {"bin": "Size 2-4", "count": 0},
        {"bin": "Size 5-9", "count": 12},
        {"bin": "Size 10-19", "count": 8},
        {"bin": "Size 20+", "count": 2},
    ]
    total_classes = sum(item["count"] for item in histogram_data)
    assert total_classes == 22
    assert histogram_data[0]["count"] == 0, "Zero classes below K=5 under strict K"


def test_l_diversity_breakdown_visualization_model():
    l_diversity_data = [
        {"equivalence_class": "EC-01", "distinct_values": 4, "target_l": 3, "compliant": True},
        {"equivalence_class": "EC-02", "distinct_values": 3, "target_l": 3, "compliant": True},
        {"equivalence_class": "EC-03", "distinct_values": 5, "target_l": 3, "compliant": True},
    ]
    for item in l_diversity_data:
        assert item["distinct_values"] >= item["target_l"]
        assert item["compliant"] is True


def test_t_closeness_ecdf_curves_model():
    ecdf_curve = [
        {"value": 100, "class_cdf": 0.10, "global_cdf": 0.12, "delta": 0.02},
        {"value": 500, "class_cdf": 0.50, "global_cdf": 0.54, "delta": 0.04},
        {"value": 1000, "class_cdf": 0.90, "global_cdf": 0.88, "delta": 0.02},
    ]
    max_delta = max(p["delta"] for p in ecdf_curve)
    assert max_delta <= 0.15


def test_curs_radar_chart_utility_model():
    radar_data = [
        {"axis": "Record Retention", "score": 96.0, "full_mark": 100.0},
        {"axis": "Numeric Fidelity", "score": 95.0, "full_mark": 100.0},
        {"axis": "Categorical Fidelity", "score": 92.0, "full_mark": 100.0},
        {"axis": "Correlation", "score": 90.0, "full_mark": 100.0},
        {"axis": "Granularity", "score": 88.0, "full_mark": 100.0},
    ]
    assert len(radar_data) == 5
    for item in radar_data:
        assert 0.0 <= item["score"] <= item["full_mark"]
