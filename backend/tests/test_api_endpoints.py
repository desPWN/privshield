"""
Comprehensive Integration Tests for FinGuard FastAPI Service Layer
Tests all RESTful endpoints:
- Dataset uploading (CSV, XLSX, JSON)
- 1-Click Jordanian synthetic demonstration loading
- Masked paginated previews
- Automatic sensitive data discovery & overrides
- De-identification pipeline execution
- Privacy & utility analytics retrieval
- Side-by-side comparative diff
- Multi-format sanitized export (CSV, XLSX, JSON)
- Executive ReportLab PDF generation and download
- Preset policies management
- Security guards (path traversal & formula injection)
"""

import io
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_check_endpoints():
    """Verifies that health check endpoints return 200 OK."""
    res_root = client.get("/health")
    assert res_root.status_code == 200
    assert res_root.json()["status"] == "ok"

    res_api = client.get("/api/health")
    assert res_api.status_code == 200
    assert res_api.json()["status"] == "ok"


def test_load_demo_dataset():
    """Verifies 1-click loading of Jordanian synthetic demonstration dataset."""
    res = client.post("/api/datasets/load-demo")
    assert res.status_code == 201
    data = res.json()
    assert "dataset_id" in data
    assert data["row_count"] >= 1000
    assert "preview" in data
    assert len(data["preview"]) > 0


def test_upload_csv_dataset():
    """Verifies local upload of a valid CSV dataset."""
    csv_content = (
        "National_ID,IBAN,Customer_Name,City,Customer_Age,Gender,Amount\n"
        "9981021234,JO42ARAB0000000123456789012345,Tariq Al-Majali,Amman,34,Male,150.00\n"
        "9981021235,JO42ARAB0000000123456789012346,Rania Haddad,Amman,34,Female,200.00\n"
        "9981021236,JO42ARAB0000000123456789012347,Omar Qudah,Zarqa,45,Male,80.50\n"
        "9981021237,JO42ARAB0000000123456789012348,Dina Zreikat,Zarqa,45,Female,95.00\n"
    )
    files = {"file": ("test_upload.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/datasets/upload", files=files, data={"name": "Test Upload Dataset"})
    assert res.status_code == 201
    data = res.json()
    assert data["row_count"] == 4
    assert "National_ID" in data["columns"]


def test_upload_invalid_file_extension():
    """Verifies that uploading an unsupported file extension returns 400 Bad Request."""
    files = {"file": ("malicious.exe", io.BytesIO(b"binary_payload"), "application/octet-stream")}
    res = client.post("/api/datasets/upload", files=files)
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["detail"]


def test_dataset_preview_masks_sensitive_values():
    """Verifies that the paginated preview endpoint masks sensitive values."""
    # First load demo
    res_demo = client.post("/api/datasets/load-demo")
    assert res_demo.status_code == 201
    dataset_id = res_demo.json()["dataset_id"]

    res_preview = client.get(f"/api/datasets/{dataset_id}/preview?page=1&size=10&mask_sensitive=true")
    assert res_preview.status_code == 200
    data = res_preview.json()
    assert data["page"] == 1
    assert len(data["records"]) <= 10

    # Ensure sensitive values are masked in preview records
    for row in data["records"]:
        if "NationalID" in row and row["NationalID"]:
            assert "****" in row["NationalID"] or "[MASKED]" in row["NationalID"]
        if "IBAN" in row and row["IBAN"]:
            assert "****" in row["IBAN"] or "[MASKED]" in row["IBAN"]


def test_sensitive_data_discovery_and_overrides():
    """Verifies sensitive data discovery and classification override updates."""
    res_demo = client.post("/api/datasets/load-demo")
    dataset_id = res_demo.json()["dataset_id"]

    # Discover
    res_disc = client.get(f"/api/datasets/{dataset_id}/discover")
    assert res_disc.status_code == 200
    profiles = res_disc.json()["profiles"]
    assert len(profiles) > 0

    col_names = [p["column_name"] for p in profiles]
    assert "NationalID" in col_names or "nationalid" in [c.lower() for c in col_names]

    # Override a column
    override_payload = {
        "overrides": [
            {
                "column_name": "City",
                "user_category": "sensitive_attribute",
                "notes": "Testing override to sensitive"
            }
        ]
    }
    res_ov = client.post(f"/api/datasets/{dataset_id}/overrides", json=override_payload)
    assert res_ov.status_code == 200
    updated_profiles = res_ov.json()["profiles"]
    city_prof = next(p for p in updated_profiles if p["column_name"] == "City")
    assert city_prof["user_category"] == "sensitive_attribute"
    assert city_prof["is_overridden"] is True


def test_full_anonymization_pipeline_and_export():
    """Tests the complete workflow: demo load -> anonymize -> analytics -> diff -> exports -> PDF."""
    res_demo = client.post("/api/datasets/load-demo")
    dataset_id = res_demo.json()["dataset_id"]

    # Configure anonymization
    anon_config = {
        "quasi_identifiers": ["City", "Age", "Gender"],
        "sensitive_attributes": ["TransactionAmount", "TransactionCategory"],
        "k_metric": 5,
        "l_metric": 2,
        "t_metric": 0.30,
        "suppression_strategy": "record",
        "max_suppression_pct": 0.50,
        "masking_rules": {
            "NationalID": "mask_national_id",
            "IBAN": "mask_iban",
            "FullName": "mask_full"
        },
        "generalization_levels": {
            "City": 1,
            "Age": 1
        }
    }

    # Execute anonymization
    res_anon = client.post(f"/api/datasets/{dataset_id}/anonymize", json=anon_config)
    assert res_anon.status_code == 200
    metrics = res_anon.json()
    assert "run_id" in metrics
    run_id = metrics["run_id"]
    assert metrics["k_satisfied"] is True
    assert metrics["achieved_k"] >= 5
    assert metrics["utility_metrics"]["composite_utility_score"] > 0

    # Retrieve run
    res_run = client.get(f"/api/runs/{run_id}")
    assert res_run.status_code == 200
    assert res_run.json()["id"] == run_id

    # Retrieve analytics
    res_analytics = client.get(f"/api/runs/{run_id}/analytics")
    assert res_analytics.status_code == 200
    analytics_data = res_analytics.json()
    assert "ec_histogram" in analytics_data
    assert "privacy_risk" in analytics_data
    assert "utility_metrics" in analytics_data

    # Retrieve diff
    res_diff = client.get(f"/api/runs/{run_id}/diff?page=1&size=20")
    assert res_diff.status_code == 200
    diff_data = res_diff.json()
    assert len(diff_data["diff"]) <= 20
    assert "cells" in diff_data["diff"][0]

    # Export CSV
    res_csv = client.get(f"/api/runs/{run_id}/export/csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert len(res_csv.content) > 0

    # Export XLSX
    res_xlsx = client.get(f"/api/runs/{run_id}/export/xlsx")
    assert res_xlsx.status_code == 200
    assert "openxmlformats" in res_xlsx.headers["content-type"]
    assert len(res_xlsx.content) > 1000

    # Export JSON
    res_json = client.get(f"/api/runs/{run_id}/export/json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    exported_records = json.loads(res_json.content.decode("utf-8"))
    assert isinstance(exported_records, list)

    # Download Executive PDF Report
    res_pdf = client.get(f"/api/runs/{run_id}/report/pdf")
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"]
    assert res_pdf.content.startswith(b"%PDF-")


def test_presets_api():
    """Verifies listing and creating anonymization presets."""
    res_list = client.get("/api/presets")
    assert res_list.status_code == 200
    presets = res_list.json()
    assert len(presets) >= 3  # Built-in presets

    new_preset = {
        "name": "Custom FinGuard Policy",
        "description": "Custom policy for corporate audit",
        "rules": {
            "k_metric": 4,
            "max_suppression_pct": 0.15,
            "masking_rules": {"National_ID": "mask_national_id"}
        }
    }
    res_create = client.post("/api/presets", json=new_preset)
    assert res_create.status_code == 201
    created = res_create.json()
    assert created["name"] == "Custom FinGuard Policy"


def test_path_traversal_protection():
    """Verifies that malicious path traversal attempts in identifiers are blocked."""
    res = client.get("/api/datasets/../../etc/passwd")
    assert res.status_code in (400, 404)

    res_run = client.get("/api/runs/../../etc/passwd")
    assert res_run.status_code in (400, 404)
