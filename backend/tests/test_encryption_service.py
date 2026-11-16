"""
Unit tests for PrivShield EncryptionService.
Tests AES-256-GCM authenticated file and binary encryption,
Fernet token encryption, deterministic/random token generation,
and admin passkey verification.
"""

import os
from pathlib import Path
import pytest
from cryptography.exceptions import InvalidTag

from backend.app.services.encryption_service import EncryptionService


def test_aes_gcm_bytes_roundtrip():
    plaintext = b"Highly confidential medical diagnosis and credit record"
    ciphertext = EncryptionService.encrypt_bytes_aes_gcm(plaintext)

    assert ciphertext != plaintext
    assert len(ciphertext) > len(plaintext)  # Nonce + tag overhead

    decrypted = EncryptionService.decrypt_bytes_aes_gcm(ciphertext)
    assert decrypted == plaintext


def test_aes_gcm_tamper_detection():
    plaintext = b"Tamper-evident payload"
    ciphertext = bytearray(EncryptionService.encrypt_bytes_aes_gcm(plaintext))

    # Tamper with the last byte of ciphertext (auth tag)
    ciphertext[-1] ^= 0xFF

    with pytest.raises(Exception):
        EncryptionService.decrypt_bytes_aes_gcm(bytes(ciphertext))


def test_aes_gcm_file_encryption_roundtrip(tmp_path: Path):
    plain_file = tmp_path / "sample.csv"
    raw_content = b"id,name,salary\n1,Alice,120000\n2,Bob,95000\n"
    plain_file.write_bytes(raw_content)

    enc_file = tmp_path / "sample.csv.enc"
    EncryptionService.encrypt_file(plain_file, enc_file)

    assert enc_file.exists()
    assert enc_file.read_bytes() != raw_content

    decrypted_bytes = EncryptionService.decrypt_file(enc_file)
    assert decrypted_bytes == raw_content


def test_fernet_string_encryption_roundtrip():
    original = "NationalID-9981240192"
    encrypted = EncryptionService.encrypt_string(original)

    assert encrypted != original
    decrypted = EncryptionService.decrypt_string(encrypted)
    assert decrypted == original


def test_pseudonym_token_generation():
    token1 = EncryptionService.generate_token(prefix="PSEUDO", length=12)
    token2 = EncryptionService.generate_token(prefix="PSEUDO", length=12)

    assert token1.startswith("PSEUDO-")
    assert token2.startswith("PSEUDO-")
    assert token1 != token2  # Unique randomness


def test_salted_token_determinism():
    val = "patient_12345"
    t1 = EncryptionService.generate_salted_token(val, salt="TestSalt1")
    t2 = EncryptionService.generate_salted_token(val, salt="TestSalt1")
    t3 = EncryptionService.generate_salted_token(val, salt="DifferentSalt")

    assert t1.startswith("TOK-")
    assert t1 == t2
    assert t1 != t3


def test_admin_passkey_verification():
    assert EncryptionService.verify_admin_passkey("PrivShieldAdmin2026!") is True
    assert EncryptionService.verify_admin_passkey("WrongPasskey") is False
    assert EncryptionService.verify_admin_passkey("") is False
