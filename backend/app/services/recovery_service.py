"""
PrivShield Recovery Service
Implements Mode 1 Reversible Pseudonymization vault architecture:
1. Reversible token lookup with passkey verification and original value decryption.
2. Full dataset restoration from AES-256-GCM encrypted storage.
3. Pseudonymization transformation with relational token vault persistence.
4. Immutable audit logging of all de-pseudonymization and recovery actions.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.security import resolve_safe_path
from backend.app.db.database import DatabaseRepository
from backend.app.models.schemas import RecoveryAuditLogItem, TokenLookupResponse
from backend.app.services.encryption_service import EncryptionService


class RecoveryService:
    @classmethod
    def pseudonymize_dataframe(
        cls,
        df: pd.DataFrame,
        dataset_id: str,
        run_id: str,
        direct_identifiers: List[str],
        token_prefix: str = "PSEUDO",
    ) -> Tuple[pd.DataFrame, int]:
        """
        Replaces direct identifier values with cryptographic pseudonym tokens
        and records encrypted mappings in the SQLite vault.
        """
        pseudonymized_df = df.copy()
        mappings: List[Dict[str, Any]] = []

        for col in direct_identifiers:
            if col not in pseudonymized_df.columns:
                continue

            # Generate tokens per row
            new_col_vals = []
            for row_idx, val in enumerate(pseudonymized_df[col]):
                if pd.isna(val):
                    new_col_vals.append(val)
                    continue

                orig_str = str(val)
                token = EncryptionService.generate_token(prefix=token_prefix, length=12)
                encrypted_val = EncryptionService.encrypt_string(orig_str)

                mappings.append({
                    "column_name": col,
                    "row_index": row_idx,
                    "token": token,
                    "encrypted_original_value": encrypted_val,
                })
                new_col_vals.append(token)

            pseudonymized_df[col] = new_col_vals

        token_count = DatabaseRepository.store_token_mappings(dataset_id, run_id, mappings)
        return pseudonymized_df, token_count

    @classmethod
    def lookup_token(
        cls,
        token: str,
        passkey: str,
        run_id: Optional[str] = None,
        column_name: Optional[str] = None,
        actor: str = "admin",
        ip_address: str = "127.0.0.1",
        justification: str = "Authorized token recovery",
    ) -> TokenLookupResponse:
        """
        Recovers a single original value given its pseudonym token,
        verifying the admin passkey and writing an immutable audit log entry.
        """
        if not EncryptionService.verify_admin_passkey(passkey):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid administrator recovery passkey.",
            )

        mapping = DatabaseRepository.lookup_token(token, run_id=run_id, column_name=column_name)
        if not mapping:
            DatabaseRepository.log_recovery_audit(
                dataset_id=mapping.get("dataset_id", "unknown") if mapping else "unknown",
                run_id=run_id,
                actor=actor,
                ip_address=ip_address,
                action="restore_single_record",
                token_queried=token,
                records_recovered=0,
                justification=f"FAILED_LOOKUP: {justification}",
            )
            return TokenLookupResponse(
                found=False,
                original_value=None,
                column_name=column_name,
                run_id=run_id,
                token=token,
            )

        decrypted_val = EncryptionService.decrypt_string(mapping["encrypted_original_value"])

        DatabaseRepository.log_recovery_audit(
            dataset_id=mapping["dataset_id"],
            run_id=mapping.get("run_id"),
            actor=actor,
            ip_address=ip_address,
            action="restore_single_record",
            token_queried=token,
            records_recovered=1,
            justification=justification,
        )

        return TokenLookupResponse(
            found=True,
            original_value=decrypted_val,
            column_name=mapping.get("column_name"),
            run_id=mapping.get("run_id"),
            token=token,
        )

    @classmethod
    def restore_dataset(
        cls,
        dataset_id: str,
        passkey: str,
        actor: str = "admin",
        ip_address: str = "127.0.0.1",
        justification: str = "Authorized full dataset restore",
    ) -> bytes:
        """
        Decrypts and restores the original raw dataset from encrypted storage,
        verifying the admin passkey and logging the action.
        """
        if not EncryptionService.verify_admin_passkey(passkey):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid administrator recovery passkey.",
            )

        dataset = DatabaseRepository.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset '{dataset_id}' not found.",
            )

        # Check for encrypted file first
        enc_path = resolve_safe_path(settings.RAW_STORAGE_DIR, f"{dataset_id}.enc")
        if enc_path.exists():
            decrypted_bytes = EncryptionService.decrypt_file(enc_path)
            row_count = dataset.get("row_count", 0)
            DatabaseRepository.log_recovery_audit(
                dataset_id=dataset_id,
                run_id=None,
                actor=actor,
                ip_address=ip_address,
                action="restore_dataset",
                token_queried=None,
                records_recovered=row_count,
                justification=justification,
            )
            return decrypted_bytes

        # Check raw storage path
        raw_path = Path(dataset["raw_storage_path"])
        if raw_path.exists():
            if raw_path.suffix == ".enc" or dataset.get("is_encrypted") == 1:
                data_bytes = EncryptionService.decrypt_file(raw_path)
            else:
                data_bytes = raw_path.read_bytes()
            row_count = dataset.get("row_count", 0)
            DatabaseRepository.log_recovery_audit(
                dataset_id=dataset_id,
                run_id=None,
                actor=actor,
                ip_address=ip_address,
                action="restore_dataset",
                token_queried=None,
                records_recovered=row_count,
                justification=justification,
            )
            return data_bytes

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encrypted storage for dataset '{dataset_id}' not found on disk.",
        )

    @classmethod
    def get_audit_logs(cls, limit: int = 100) -> List[RecoveryAuditLogItem]:
        """Returns immutable recovery audit logs."""
        rows = DatabaseRepository.get_recovery_audit_logs(limit=limit)
        return [
            RecoveryAuditLogItem(
                id=r["id"],
                dataset_id=r["dataset_id"],
                run_id=r.get("run_id"),
                actor=r["actor"],
                ip_address=r["ip_address"],
                action=r["action"],
                token_queried=r.get("token_queried"),
                records_recovered=r["records_recovered"],
                justification=r["justification"],
                timestamp=str(r["timestamp"]),
            )
            for r in rows
        ]
