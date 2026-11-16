"""
tests_e2e/tier2_boundaries/test_b08_recovery_passkey_boundaries.py
Boundary Testing: Invalid passkeys, edge credentials, and cryptographic tamper attacks in recovery.
"""

import pandas as pd
import pytest
from tests_e2e.test_contracts import get_recovery_vault, ReferenceEncryptionService


def test_recovery_empty_and_whitespace_passkey_fails():
    vault = get_recovery_vault()
    df = pd.DataFrame({"ID": [1, 2], "Val": ["A", "B"]})
    vault.store_dataset_mode1("ds-b08-1", df, {"TOK-1": "A"})

    for bad_passkey in ["", " ", "   ", "\t", "\n"]:
        with pytest.raises(PermissionError):
            vault.lookup_token("ds-b08-1", "TOK-1", bad_passkey)

        with pytest.raises(PermissionError):
            vault.restore_dataset("ds-b08-1", bad_passkey)


def test_recovery_wrong_passkey_brute_force_resistance():
    vault = get_recovery_vault()
    df = pd.DataFrame({"ID": [1], "Val": ["Secret"]})
    vault.store_dataset_mode1("ds-b08-2", df, {"TOK-S": "Secret"})

    attempted_keys = ["admin", "root", "123456", "password", "AdminPasskey2025!", "adminpasskey2026!"]
    for attempt in attempted_keys:
        with pytest.raises(PermissionError):
            vault.lookup_token("ds-b08-2", "TOK-S", attempt)


def test_recovery_nonexistent_dataset_and_token():
    vault = get_recovery_vault()
    with pytest.raises(KeyError):
        vault.restore_dataset("nonexistent-dataset-id", "AdminPasskey2026!")

    with pytest.raises(KeyError):
        vault.lookup_token("nonexistent-dataset-id", "TOK-X", "AdminPasskey2026!")


def test_ciphertext_bit_flip_tamper_defense():
    service = ReferenceEncryptionService()
    raw = b"Critical financial record: AccountBalance=5000000"
    enc = bytearray(service.encrypt_bytes(raw))

    # Flip bits across multiple positions
    for pos in [0, 5, 15, len(enc) - 1]:
        corrupt = bytearray(enc)
        corrupt[pos] ^= 0x01
        with pytest.raises(ValueError):
            service.decrypt_bytes(bytes(corrupt))
