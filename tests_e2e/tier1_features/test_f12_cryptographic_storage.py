"""
tests_e2e/tier1_features/test_f12_cryptographic_storage.py
Feature 12: At-Rest Cryptographic Storage & EncryptionService.
Validates AES-256-GCM authenticated dataset encryption at rest, Fernet tokens, and tamper detection.
"""

import pytest
from tests_e2e.test_contracts import ReferenceEncryptionService


def test_aes_gcm_dataset_encryption_and_decryption():
    service = ReferenceEncryptionService()
    raw_payload = b"PatientID,ICD10,Diagnosis\nP101,E11.9,Type 2 Diabetes"
    encrypted = service.encrypt_bytes(raw_payload)

    assert encrypted != raw_payload
    decrypted = service.decrypt_bytes(encrypted)
    assert decrypted == raw_payload


def test_aes_gcm_tamper_detection_raises_error():
    service = ReferenceEncryptionService()
    raw_payload = b"Confidential banking transaction data"
    encrypted = bytearray(service.encrypt_bytes(raw_payload))

    # Tamper with byte in ciphertext
    encrypted[-1] ^= 0xFF

    with pytest.raises(ValueError, match="tampered"):
        service.decrypt_bytes(bytes(encrypted))


def test_encryption_key_isolation():
    service1 = ReferenceEncryptionService(key=b"KeyAlpha1234567890123456789012!")
    service2 = ReferenceEncryptionService(key=b"KeyBeta987654321098765432109876!")

    data = b"Secret employee compensation records"
    enc = service1.encrypt_bytes(data)

    with pytest.raises(ValueError):
        service2.decrypt_bytes(enc)


def test_truncated_ciphertext_detection():
    service = ReferenceEncryptionService()
    with pytest.raises(ValueError, match="truncated"):
        service.decrypt_bytes(b"short")


def test_empty_payload_encryption():
    service = ReferenceEncryptionService()
    empty = b""
    enc = service.encrypt_bytes(empty)
    dec = service.decrypt_bytes(enc)
    assert dec == empty
