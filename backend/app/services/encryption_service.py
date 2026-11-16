"""
PrivShield Encryption Service
Provides:
1. AES-256-GCM authenticated file and binary encryption at rest.
2. Fernet symmetric authenticated string and field encryption for reversible token mappings.
3. Pseudonymization token generation (salted HMAC-SHA256 and random tokens).
4. Administrator passkey verification for recovery operations.
"""

import base64
import hashlib
import hmac
import os
from pathlib import Path
from typing import Optional
import uuid

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from backend.app.core.config import settings

_DEFAULT_RECOVERY_PASSKEY = os.environ.get("PRIVSHIELD_RECOVERY_KEY", "PrivShieldAdmin2026!")


class EncryptionService:
    _master_key: Optional[bytes] = None
    _fernet_instance: Optional[Fernet] = None

    @classmethod
    def _get_key_file_path(cls) -> Path:
        return settings.DATA_DIR / ".vault_key"

    @classmethod
    def get_master_key(cls) -> bytes:
        """Returns 32-byte master key, generating and persisting if not present."""
        if cls._master_key is not None:
            return cls._master_key

        key_path = cls._get_key_file_path()
        if key_path.exists():
            try:
                cls._master_key = key_path.read_bytes()
                if len(cls._master_key) == 32:
                    return cls._master_key
            except Exception:
                pass

        # Generate a new 256-bit key
        new_key = AESGCM.generate_key(bit_length=256)
        try:
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_bytes(new_key)
        except Exception:
            pass
        cls._master_key = new_key
        return cls._master_key

    @classmethod
    def get_fernet(cls) -> Fernet:
        """Returns Fernet cipher instance derived from master key."""
        if cls._fernet_instance is not None:
            return cls._fernet_instance

        master_key = cls.get_master_key()
        # Derive a 32-byte Fernet-compatible urlsafe base64 key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"PrivShield_Fernet_Salt_2026",
            iterations=100_000,
        )
        fernet_key = base64.urlsafe_b64encode(kdf.derive(master_key))
        cls._fernet_instance = Fernet(fernet_key)
        return cls._fernet_instance

    @classmethod
    def encrypt_bytes_aes_gcm(cls, data: bytes) -> bytes:
        """
        Encrypts plaintext bytes using AES-256-GCM.
        Prepends a 12-byte random nonce to the ciphertext.
        """
        key = cls.get_master_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    @classmethod
    def decrypt_bytes_aes_gcm(cls, payload: bytes) -> bytes:
        """
        Decrypts AES-256-GCM payload with prepended 12-byte nonce.
        """
        if len(payload) < 28:
            raise ValueError("Ciphertext too short to contain nonce and authentication tag.")
        nonce = payload[:12]
        ciphertext = payload[12:]
        key = cls.get_master_key()
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    @classmethod
    def encrypt_file(cls, input_path: Path, output_path: Path) -> None:
        """Reads file, encrypts with AES-256-GCM, and writes to output_path."""
        raw_data = input_path.read_bytes()
        encrypted = cls.encrypt_bytes_aes_gcm(raw_data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(encrypted)

    @classmethod
    def decrypt_file(cls, encrypted_path: Path) -> bytes:
        """Reads encrypted file and decrypts it with AES-256-GCM."""
        encrypted_data = encrypted_path.read_bytes()
        return cls.decrypt_bytes_aes_gcm(encrypted_data)

    @classmethod
    def encrypt_string(cls, plaintext: str) -> str:
        """Encrypts string using Fernet and returns urlsafe base64 string."""
        fernet = cls.get_fernet()
        return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    @classmethod
    def decrypt_string(cls, ciphertext: str) -> str:
        """Decrypts Fernet ciphertext string back to plaintext string."""
        fernet = cls.get_fernet()
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    @classmethod
    def generate_token(cls, prefix: str = "PSEUDO", length: int = 12) -> str:
        """Generates random high-entropy pseudonym token: PSEUDO-<HEX>."""
        raw_hex = uuid.uuid4().hex.upper()[:length]
        return f"{prefix}-{raw_hex}"

    @classmethod
    def generate_salted_token(cls, value: str, salt: str = "PrivShield_Salt_2026") -> str:
        """Generates deterministic HMAC-SHA256 pseudonym token."""
        h = hmac.new(salt.encode("utf-8"), str(value).encode("utf-8"), hashlib.sha256).hexdigest()
        return f"TOK-{h[:12].upper()}"

    @classmethod
    def verify_admin_passkey(cls, passkey: str) -> bool:
        """Constant-time verification of administrator recovery passkey."""
        if not passkey:
            return False
        return hmac.compare_digest(passkey.strip(), _DEFAULT_RECOVERY_PASSKEY.strip())
