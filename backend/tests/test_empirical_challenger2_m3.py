"""
Empirical Challenger 2 Verification Suite for Milestone M3.
Focus: State Transitions, API Contract Integrity, Security Validation & Adversarial Boundaries.
"""

import io
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.encryption_service import _DEFAULT_RECOVERY_PASSKEY

client = TestClient(app)


@pytest.fixture(scope="module")
def loaded_dataset_id():
    """Provides an active dataset ID for testing overrides and recovery."""
    csv_content = (
        "MRN,PatientName,Age,Gender,ICD10,Diagnosis,Ward,AdmissionDate\n"
        "MRN10001,John Doe,45,Male,E11.9,Type 2 Diabetes,Ward A,2026-01-10\n"
        "MRN10002,Jane Smith,45,Female,I10,Essential Hypertension,Ward A,2026-01-11\n"
        "MRN10003,Bob Johnson,52,Male,E11.9,Type 2 Diabetes,Ward B,2026-01-12\n"
        "MRN10004,Alice Brown,52,Female,I10,Essential Hypertension,Ward B,2026-01-13\n"
    )
    files = {"file": ("patients.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/datasets/upload", files=files, data={"name": "Hospital Patients"})
    assert res.status_code == 201
    return res.json()["dataset_id"]


class TestDiscoveryViewOverridesContract:
    """Verifies DiscoveryView override payload structure against FastAPI backend."""

    def test_update_overrides_valid_payload(self, loaded_dataset_id):
        payload = {
            "overrides": [
                {"column_name": "PatientName", "user_category": "direct_identifier"},
                {"column_name": "Age", "user_category": "quasi_identifier"},
                {"column_name": "Diagnosis", "user_category": "sensitive_attribute"},
                {"column_name": "Ward", "user_category": "insensitive"},
            ]
        }
        res = client.post(f"/api/datasets/{loaded_dataset_id}/overrides", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["dataset_id"] == loaded_dataset_id
        assert "profiles" in data
        assert len(data["profiles"]) > 0

        # Verify overridden profiles are returned with correct user_category
        profile_map = {p["column_name"]: p for p in data["profiles"]}
        assert profile_map["PatientName"]["user_category"] == "direct_identifier"
        assert profile_map["Age"]["user_category"] == "quasi_identifier"
        assert profile_map["Diagnosis"]["user_category"] == "sensitive_attribute"
        assert profile_map["Ward"]["user_category"] == "insensitive"

    def test_update_overrides_empty_list_accepted(self, loaded_dataset_id):
        res = client.post(f"/api/datasets/{loaded_dataset_id}/overrides", json={"overrides": []})
        assert res.status_code == 200

    def test_update_overrides_invalid_category_rejected(self, loaded_dataset_id):
        payload = {
            "overrides": [
                {"column_name": "PatientName", "user_category": "invalid_category"}
            ]
        }
        res = client.post(f"/api/datasets/{loaded_dataset_id}/overrides", json=payload)
        assert res.status_code == 422

    def test_update_overrides_missing_overrides_key_rejected(self, loaded_dataset_id):
        res = client.post(f"/api/datasets/{loaded_dataset_id}/overrides", json={})
        assert res.status_code == 422


class TestRecoveryApiSecurityContract:
    """Verifies Recovery API admin passkey and token lookup security."""

    def test_lookup_token_wrong_passkey_forbidden(self):
        payload = {
            "token": "TOKEN-XYZ-1234",
            "passkey": "wrong_password_attempt",
            "justification": "Adversarial test",
        }
        res = client.post("/api/recovery/lookup-token", json=payload)
        assert res.status_code == 403
        assert "passkey" in res.json()["detail"].lower()

    def test_lookup_token_empty_passkey_forbidden(self):
        payload = {
            "token": "TOKEN-XYZ-1234",
            "passkey": "",
            "justification": "Adversarial test",
        }
        res = client.post("/api/recovery/lookup-token", json=payload)
        assert res.status_code == 403

    def test_lookup_token_valid_passkey_not_found_token(self):
        payload = {
            "token": "NONEXISTENT-TOKEN-99999",
            "passkey": _DEFAULT_RECOVERY_PASSKEY,
            "justification": "Valid lookup test",
        }
        res = client.post("/api/recovery/lookup-token", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["found"] is False
        assert data["token"] == "NONEXISTENT-TOKEN-99999"

    def test_restore_dataset_wrong_passkey_forbidden(self, loaded_dataset_id):
        payload = {
            "dataset_id": loaded_dataset_id,
            "passkey": "invalid_master_passkey",
            "justification": "Adversarial restore test",
        }
        res = client.post("/api/recovery/restore-dataset", json=payload)
        assert res.status_code == 403

    def test_restore_dataset_empty_passkey_forbidden(self, loaded_dataset_id):
        payload = {
            "dataset_id": loaded_dataset_id,
            "passkey": "",
            "justification": "Empty passkey test",
        }
        res = client.post("/api/recovery/restore-dataset", json=payload)
        assert res.status_code == 403

    def test_restore_dataset_nonexistent_id_404(self):
        payload = {
            "dataset_id": "nonexistent-dataset-id-00000000",
            "passkey": _DEFAULT_RECOVERY_PASSKEY,
            "justification": "404 test",
        }
        res = client.post("/api/recovery/restore-dataset", json=payload)
        assert res.status_code == 404

    def test_audit_logs_contract_and_zero_pii(self):
        res = client.get("/api/recovery/audit-logs")
        assert res.status_code == 200
        logs = res.json()
        assert isinstance(logs, list)

        # Invariant: zero PII in audit log fields
        for log in logs:
            assert "id" in log
            assert "timestamp" in log
            assert "action" in log
            assert "actor" in log
            token = log.get("token_queried")
            if token:
                assert not any(name in token for name in ["John Doe", "Jane Smith", "Tariq Al-Majali"])


class TestMultiIndustryEndpoints:
    """Verifies industry profile and demo dataset loading endpoints."""

    def test_list_industry_profiles(self):
        res = client.get("/api/profiles")
        assert res.status_code == 200
        profiles = res.json()
        assert isinstance(profiles, list)
        profile_ids = [p["id"] for p in profiles]
        for expected in ["healthcare", "finance", "education", "government", "hr", "ecommerce", "custom"]:
            assert expected in profile_ids

    @pytest.mark.parametrize("industry", ["healthcare", "finance", "education", "hr", "ecommerce"])
    def test_load_industry_demo(self, industry):
        res = client.post(f"/api/datasets/load-industry-demo/{industry}")
        assert res.status_code in [200, 201]
        data = res.json()
        assert "dataset_id" in data
        assert data["row_count"] >= 100
        assert "columns" in data
        assert len(data["columns"]) > 0
