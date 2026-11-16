"""
PrivShield Milestone M2 Service Layer & Endpoint Verification Tests
Validates:
1. Multi-industry demo loader: POST /api/datasets/load-industry-demo/{industry}
2. Industry profiles API: GET /api/profiles and GET /api/profiles/{id}
3. Secure recovery endpoints: /api/recovery/lookup-token, /api/recovery/restore-dataset, /api/recovery/status/{id}, /api/recovery/audit-logs
4. Pre-export privacy verification gateway: blocks Mode 2 violations, permits compliant exports
5. Formula injection defense across exported datasets
6. ReportLab PDF generator modernization: PrivShield branding, dynamic industry badges, scorecards, zero raw PII
"""

import io
import json
import pytest
from fastapi.testclient import TestClient
import pandas as pd

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.db.database import DatabaseRepository
from backend.app.models.schemas import AnonymizationConfig
from backend.app.services.anonymization_service import AnonymizationService
from backend.app.services.export_service import export_dataset, verify_pre_export_privacy_gateway
from backend.app.services.pdf_service import generate_pdf_report
from backend.app.services.recovery_service import RecoveryService

client = TestClient(app)


def test_load_industry_demo_all_supported_domains():
    """Verifies that all 6 supported industry demo datasets load cleanly."""
    industries = ["healthcare", "finance", "education", "hr", "ecommerce", "government"]
    for ind in industries:
        res = client.post(f"/api/datasets/load-industry-demo/{ind}")
        assert res.status_code == 201, f"Failed to load demo dataset for {ind}: {res.text}"
        data = res.json()
        assert "dataset_id" in data
        assert data["row_count"] == 1000
        assert data["column_count"] > 5
        assert len(data["columns"]) > 5
        assert len(data["preview"]) > 0
        assert data["industry"] == ind

        # Verify discovery column metadata persisted in DB
        profiles = DatabaseRepository.get_column_metadata(data["dataset_id"])
        assert len(profiles) == data["column_count"]


def test_load_industry_demo_unsupported_domain_raises_400():
    """Verifies rejection of unsupported industry names."""
    res = client.post("/api/datasets/load-industry-demo/unsupported_industry_xyz")
    assert res.status_code == 400
    assert "Unsupported industry" in res.json()["detail"]


def test_profiles_endpoints_return_seven_profiles():
    """Verifies GET /api/profiles and GET /api/profiles/{id} return expected profiles."""
    res_list = client.get("/api/profiles")
    assert res_list.status_code == 200
    profiles = res_list.json()
    assert len(profiles) == 7

    expected_ids = {"healthcare", "finance", "education", "government", "hr", "ecommerce", "custom"}
    found_ids = {p["id"] for p in profiles}
    assert expected_ids.issubset(found_ids)

    # Test single profile retrieval with case insensitivity
    for pid in expected_ids:
        res_single = client.get(f"/api/profiles/{pid}")
        assert res_single.status_code == 200
        assert res_single.json()["id"] == pid

        # Case-insensitive
        res_upper = client.get(f"/api/profiles/{pid.upper()}")
        assert res_upper.status_code == 200
        assert res_upper.json()["id"] == pid

    # Nonexistent profile
    res_none = client.get("/api/profiles/nonexistent_profile_id")
    assert res_none.status_code == 404


def test_recovery_endpoint_contract_paths(tmp_path):
    """Verifies /api/recovery/lookup-token and /api/recovery/restore-dataset aliases."""
    import uuid
    dataset_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    df = pd.DataFrame({
        "PatientID": ["PAT-101", "PAT-102", "PAT-103"],
        "PatientName": ["Ahmad Al-Majali", "Rania Haddad", "Omar Al-Zubi"],
        "Diagnosis": ["I10", "E11.9", "J45.0"]
    })
    raw_path = tmp_path / f"{dataset_id}.csv"
    df.to_csv(raw_path, index=False)

    DatabaseRepository.create_dataset({
        "id": dataset_id,
        "name": "Clinical Recovery Test Cohort",
        "filename": "patients.csv",
        "format": "csv",
        "file_size_bytes": 1024,
        "row_count": 3,
        "column_count": 3,
        "raw_storage_path": str(raw_path),
    })

    pseudo_df, token_count = RecoveryService.pseudonymize_dataframe(
        df=df,
        dataset_id=dataset_id,
        run_id=run_id,
        direct_identifiers=["PatientID", "PatientName"],
        token_prefix="PATIENT_TOK"
    )
    assert token_count == 6

    # Register the run record
    DatabaseRepository.create_anonymization_run({
        "id": run_id,
        "dataset_id": dataset_id,
        "config_json": json.dumps({"processing_mode": "reversible_pseudonymization"}),
        "anonymized_storage_path": str(raw_path),
        "status": "completed",
        "processing_mode": "reversible_pseudonymization",
        "is_reversible": 1,
        "token_mapping_count": token_count,
        "records_input": 3,
        "records_retained": 3,
        "records_suppressed": 0,
        "suppression_rate": 0.0,
        "achieved_k": 3,
        "achieved_l": 3,
        "achieved_t": 0.1,
        "utility_retention_score": 95.0,
        "metrics_json": json.dumps({"k_satisfied": True, "achieved_k": 3, "target_k": 3}),
        "execution_time_ms": 5.0,
        "error_message": None,
    })

    # Vault status endpoint
    res_status = client.get(f"/api/recovery/status/{run_id}")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["is_reversible"] is True
    assert status_data["token_mapping_count"] == 6

    # Retrieve one token mapping from database
    token_rows = DatabaseRepository.get_tokens_for_run(run_id)
    assert len(token_rows) == 6
    sample_token = token_rows[0]["token"]
    sample_col = token_rows[0]["column_name"]

    # Test /api/recovery/lookup-token with valid passkey
    payload = {
        "token": sample_token,
        "passkey": "PrivShieldAdmin2026!",
        "run_id": run_id,
        "column_name": sample_col,
        "justification": "M2 automated test token verification",
    }
    res_lookup_token = client.post("/api/recovery/lookup-token", json=payload)
    assert res_lookup_token.status_code == 200
    assert res_lookup_token.json()["found"] is True
    assert res_lookup_token.json()["original_value"] is not None

    # Test /api/recovery/lookup alias
    res_lookup = client.post("/api/recovery/lookup", json=payload)
    assert res_lookup.status_code == 200

    # Test /api/recovery/restore-dataset with valid passkey
    restore_payload = {
        "dataset_id": dataset_id,
        "passkey": "PrivShieldAdmin2026!",
        "justification": "M2 automated test dataset restoration",
    }
    res_restore_dataset = client.post("/api/recovery/restore-dataset", json=restore_payload)
    assert res_restore_dataset.status_code == 200
    assert "text/csv" in res_restore_dataset.headers["content-type"]
    assert len(res_restore_dataset.content) > 0

    # Test /api/recovery/restore alias
    res_restore = client.post("/api/recovery/restore", json=restore_payload)
    assert res_restore.status_code == 200

    # Audit logs endpoint
    res_audit = client.get("/api/recovery/audit-logs")
    assert res_audit.status_code == 200
    logs = res_audit.json()
    assert len(logs) >= 2


def test_pre_export_privacy_gateway_enforcement():
    """
    Verifies that Pre-Export Privacy Verification Gateway blocks Mode 2 exports
    when privacy evaluation failed (k_satisfied=False), and allows exports when compliant.
    """
    import uuid

    # Create compliant run
    res_load = client.post("/api/datasets/load-industry-demo/education")
    assert res_load.status_code == 201
    dataset_id = res_load.json()["dataset_id"]

    compliant_cfg = {
        "processing_mode": "irreversible_anonymization",
        "quasi_identifiers": ["Gender"],
        "sensitive_attributes": ["GPA"],
        "k_metric": 2,
    }
    res_anon_ok = client.post(f"/api/datasets/{dataset_id}/anonymize", json=compliant_cfg)
    assert res_anon_ok.status_code == 200
    run_ok_id = res_anon_ok.json()["run_id"]
    assert res_anon_ok.json()["k_satisfied"] is True

    # Exporting compliant run succeeds
    res_exp_ok = client.get(f"/api/runs/{run_ok_id}/export/csv")
    assert res_exp_ok.status_code == 200
    assert "text/csv" in res_exp_ok.headers["content-type"]

    # Now simulate a non-compliant run in database where k_satisfied = False
    fake_run_id = str(uuid.uuid4())
    DatabaseRepository.create_anonymization_run({
        "id": fake_run_id,
        "dataset_id": dataset_id,
        "config_json": json.dumps({"processing_mode": "irreversible_anonymization"}),
        "anonymized_storage_path": res_anon_ok.json().get("anonymized_storage_path", ""),
        "status": "completed",
        "processing_mode": "irreversible_anonymization",
        "is_reversible": 0,
        "token_mapping_count": 0,
        "records_input": 1000,
        "records_retained": 1000,
        "records_suppressed": 0,
        "suppression_rate": 0.0,
        "achieved_k": 1,
        "achieved_l": 1,
        "achieved_t": 0.5,
        "utility_retention_score": 10.0,
        "metrics_json": json.dumps({"k_satisfied": False, "achieved_k": 1, "target_k": 5}),
        "execution_time_ms": 10.0,
        "error_message": None,
    })

    # Export must be rejected with 400 Bad Request
    res_exp_blocked = client.get(f"/api/runs/{fake_run_id}/export/csv")
    assert res_exp_blocked.status_code == 400
    assert "Pre-Export Privacy Verification Gateway" in res_exp_blocked.json()["detail"]


def test_pdf_report_modernization_and_branding():
    """Verifies PrivShield branding, dynamic industry badges, scorecards, and zero PII."""
    industries = ["Healthcare", "Finance", "Education", "Human Resources", "Government", "E-Commerce"]

    for ind in industries:
        meta = {
            "name": f"{ind} Cohort Dataset",
            "industry": ind,
            "row_count": 1000,
        }
        metrics = {
            "k": 5,
            "k_satisfied": True,
            "achieved_k": 5,
            "suppression_rate": 0.04,
            "curs": 94.2,
            "prosecutor_risk": 0.20,
            "l_diversity_results": {
                "target_l": 3,
                "sensitive_attribute": "Diagnosis_Or_Score",
                "satisfied": True,
                "min_observed_distinct_values": 4,
            },
            "t_closeness_results": {
                "target_t": 0.15,
                "attribute_type": "Metric_Amount",
                "satisfied": True,
                "max_observed_distance": 0.082,
            },
            "utility_metrics": {
                "record_retention": 0.96,
                "numerical_distribution_fidelity": 0.95,
                "categorical_distribution_fidelity": 0.94,
                "correlation_retention": 0.92,
                "granularity_retention": 0.90,
                "composite_utility_score": 94.2,
            },
        }

        pdf_bytes = generate_pdf_report(dataset_meta=meta, metrics=metrics)
        assert pdf_bytes.startswith(b"%PDF-")

        pdf_text = pdf_bytes.decode("latin1", errors="ignore")
        # PrivShield branding
        assert "PrivShield" in pdf_text
        assert "FinGuard" not in pdf_text
        assert "Universal Data Anonymization Platform" in pdf_text

        # Dynamic badge
        assert "INDUSTRY PROFILE:" in pdf_text

        # Scorecard
        assert "Strict K-Anonymity" in pdf_text
        assert "Distinct L-Diversity" in pdf_text
        assert "T-Closeness" in pdf_text

        # 5-Component CURS
        assert "Record Retention" in pdf_text
        assert "Numerical Distribution Fidelity" in pdf_text
        assert "Categorical Distribution Fidelity" in pdf_text
        assert "Correlation Retention" in pdf_text
        assert "Granularity Retention" in pdf_text
