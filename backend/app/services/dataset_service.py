"""
PrivShield Dataset Ingestion & Management Service
Handles:
- Secure local upload of CSV, XLSX, JSON with size & type validation
- Storage isolation in storage/raw/{dataset_id}.csv
- Multi-industry synthetic demonstration dataset loader
- Built-in Jordanian demonstration dataset loader
- Paginated preview with sensitive raw values masked
- Column profile retrieval and classification overrides
"""

import io
import math
import os
from pathlib import Path
import uuid
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from fastapi import HTTPException, UploadFile, status

from backend.app.core.config import settings
from backend.app.core.security import resolve_safe_path, validate_uuid_id
from backend.app.db.database import DatabaseRepository
from backend.app.engine.discovery import discover_dataset
from backend.app.engine.masking import (
    apply_masking_rule,
    mask_card_number,
    mask_email,
    mask_full,
    mask_iban,
    mask_national_id,
    mask_partial,
    mask_phone,
)
from backend.app.models.schemas import ColumnOverrideItem, ColumnProfile
from backend.app.services.synthetic_data_service import (
    generate_industry_dataset,
    generate_hospital_dataset,
    generate_bank_transactions_dataset,
    generate_university_students_dataset,
    generate_employee_records_dataset,
    generate_customer_database_dataset,
    generate_government_dataset,
)


class SyntheticDataService:
    """Namespace providing static synthetic dataset generation methods."""
    generate_industry_dataset = staticmethod(generate_industry_dataset)
    generate_hospital_dataset = staticmethod(generate_hospital_dataset)
    generate_bank_transactions_dataset = staticmethod(generate_bank_transactions_dataset)
    generate_university_students_dataset = staticmethod(generate_university_students_dataset)
    generate_employee_records_dataset = staticmethod(generate_employee_records_dataset)
    generate_customer_database_dataset = staticmethod(generate_customer_database_dataset)
    generate_government_dataset = staticmethod(generate_government_dataset)


class DatasetService:
    @staticmethod
    def _read_dataframe_from_bytes(file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Parses file bytes into a DataFrame according to extension."""
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
            )
        try:
            if ext == ".csv":
                return pd.read_csv(io.BytesIO(file_bytes))
            elif ext == ".xlsx":
                return pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
            elif ext == ".json":
                return pd.read_json(io.BytesIO(file_bytes))
            else:
                raise ValueError("Unsupported extension")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse file '{filename}': {str(e)}",
            )

    @classmethod
    def upload_dataset(
        cls,
        file: UploadFile,
        custom_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ingests uploaded dataset file, validates size, writes to raw storage,
        executes discovery, and saves metadata into SQLite.
        """
        filename = file.filename or "uploaded_dataset.csv"
        ext = Path(filename).suffix.lower().lstrip(".")
        if f".{ext}" not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '.{ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}",
            )

        file_bytes = file.file.read()
        file_size = len(file_bytes)
        if file_size > settings.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size / (1024*1024):.1f}MB) exceeds 50MB limit.",
            )

        df = cls._read_dataframe_from_bytes(file_bytes, filename)
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded dataset contains zero records.",
            )

        dataset_id = str(uuid.uuid4())
        raw_storage_path = resolve_safe_path(
            settings.RAW_STORAGE_DIR, f"{dataset_id}.csv"
        )
        df.to_csv(raw_storage_path, index=False)

        name = custom_name or Path(filename).stem.replace("_", " ").title()

        # Database record
        dataset_meta = {
            "id": dataset_id,
            "name": name,
            "filename": filename,
            "format": ext,
            "file_size_bytes": file_size,
            "row_count": len(df),
            "column_count": len(df.columns),
            "raw_storage_path": str(raw_storage_path),
        }
        DatabaseRepository.create_dataset(dataset_meta)

        # Automatic Sensitive Data Discovery
        profiles = discover_dataset(df)
        DatabaseRepository.save_column_metadata(
            dataset_id, [p.model_dump() for p in profiles]
        )

        DatabaseRepository.log_audit(
            action="upload_dataset",
            dataset_id=dataset_id,
            details={"name": name, "rows": len(df), "columns": len(df.columns)},
        )

        preview = cls.get_dataset_preview(dataset_id, page=1, size=10, mask_sensitive=True)

        return {
            "dataset_id": dataset_id,
            "id": dataset_id,
            "name": name,
            "filename": filename,
            "format": ext,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "preview": preview["records"],
        }

    @classmethod
    def load_demo_dataset(cls) -> Dict[str, Any]:
        """Loads built-in synthetic Jordanian financial transaction demonstration dataset."""
        demo_path = settings.DEMO_DATASET_PATH
        if not demo_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Built-in demonstration dataset not found on server.",
            )

        df = pd.read_csv(demo_path)
        dataset_id = str(uuid.uuid4())
        raw_storage_path = resolve_safe_path(
            settings.RAW_STORAGE_DIR, f"{dataset_id}.csv"
        )
        df.to_csv(raw_storage_path, index=False)

        dataset_meta = {
            "id": dataset_id,
            "name": "Jordanian Financial Transactions (Synthetic Demonstration)",
            "filename": "jordan_financial_transactions.csv",
            "format": "csv",
            "file_size_bytes": os.path.getsize(demo_path),
            "row_count": len(df),
            "column_count": len(df.columns),
            "raw_storage_path": str(raw_storage_path),
        }
        DatabaseRepository.create_dataset(dataset_meta)

        profiles = discover_dataset(df)
        DatabaseRepository.save_column_metadata(
            dataset_id, [p.model_dump() for p in profiles]
        )

        DatabaseRepository.log_audit(
            action="load_demo_dataset",
            dataset_id=dataset_id,
            details={"records": len(df), "origin": str(demo_path)},
        )

        preview = cls.get_dataset_preview(dataset_id, page=1, size=10, mask_sensitive=True)

        return {
            "dataset_id": dataset_id,
            "id": dataset_id,
            "name": dataset_meta["name"],
            "filename": dataset_meta["filename"],
            "format": dataset_meta["format"],
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "preview": preview["records"],
        }

    @classmethod
    def load_industry_demo(cls, industry: str) -> Dict[str, Any]:
        """
        Loads a synthetic industry demonstration dataset:
        healthcare, finance, education, hr, ecommerce, government.
        """
        ind_clean = industry.lower().strip()
        supported_names = {
            "healthcare": "Hospital Patient Records (Healthcare Demo)",
            "hospital": "Hospital Patient Records (Healthcare Demo)",
            "finance": "Bank Transaction Records (Financial Demo)",
            "banking": "Bank Transaction Records (Financial Demo)",
            "education": "University Student Records (Education Demo)",
            "university": "University Student Records (Education Demo)",
            "hr": "Corporate Employee Records (HR Demo)",
            "employee": "Corporate Employee Records (HR Demo)",
            "ecommerce": "E-Commerce Customer Records (Retail Demo)",
            "e-commerce": "E-Commerce Customer Records (Retail Demo)",
            "customer": "E-Commerce Customer Records (Retail Demo)",
            "government": "Civil Registry Records (Government Demo)",
            "public_sector": "Civil Registry Records (Government Demo)",
        }
        if ind_clean not in supported_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported industry '{industry}'. Supported industries: healthcare, finance, education, hr, ecommerce, government.",
            )

        df = SyntheticDataService.generate_industry_dataset(ind_clean, n_rows=1000)
        dataset_id = str(uuid.uuid4())
        raw_storage_path = resolve_safe_path(
            settings.RAW_STORAGE_DIR, f"{dataset_id}.csv"
        )
        df.to_csv(raw_storage_path, index=False)

        name = supported_names[ind_clean]
        filename = f"{ind_clean}_demo_dataset.csv"
        file_size = os.path.getsize(raw_storage_path)

        dataset_meta = {
            "id": dataset_id,
            "name": name,
            "filename": filename,
            "format": "csv",
            "file_size_bytes": file_size,
            "row_count": len(df),
            "column_count": len(df.columns),
            "raw_storage_path": str(raw_storage_path),
        }
        DatabaseRepository.create_dataset(dataset_meta)

        profiles = discover_dataset(df)
        DatabaseRepository.save_column_metadata(
            dataset_id, [p.model_dump() for p in profiles]
        )

        DatabaseRepository.log_audit(
            action="load_industry_demo",
            dataset_id=dataset_id,
            details={"industry": ind_clean, "records": len(df)},
        )

        preview = cls.get_dataset_preview(dataset_id, page=1, size=10, mask_sensitive=True)

        return {
            "dataset_id": dataset_id,
            "id": dataset_id,
            "name": name,
            "filename": filename,
            "format": "csv",
            "industry": ind_clean,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "preview": preview["records"],
        }

    @classmethod
    def get_dataset_df(cls, dataset_id: str) -> pd.DataFrame:
        """Loads raw dataset into DataFrame after path traversal verification."""
        clean_id = validate_uuid_id(dataset_id)
        raw_path = resolve_safe_path(settings.RAW_STORAGE_DIR, f"{clean_id}.csv")
        if not raw_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset '{dataset_id}' raw storage file not found.",
            )
        return pd.read_csv(raw_path)

    @classmethod
    def get_dataset_preview(
        cls,
        dataset_id: str,
        page: int = 1,
        size: int = 20,
        mask_sensitive: bool = True,
    ) -> Dict[str, Any]:
        """Returns paginated rows with sensitive values masked in preview UI."""
        clean_id = validate_uuid_id(dataset_id)
        meta = DatabaseRepository.get_dataset(clean_id)
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset '{dataset_id}' not found.",
            )

        df = cls.get_dataset_df(clean_id)
        total_records = len(df)
        total_pages = max(1, math.ceil(total_records / size))
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * size
        end_idx = min(total_records, start_idx + size)
        page_df = df.iloc[start_idx:end_idx].copy()

        if mask_sensitive:
            col_meta = DatabaseRepository.get_column_metadata(clean_id)
            col_map = {c["column_name"]: c for c in col_meta}

            for col in page_df.columns:
                c_info = col_map.get(col)
                if not c_info:
                    continue
                effective_cat = c_info.get("user_category") or c_info.get("inferred_category")
                pii_type = (c_info.get("detected_pii_type") or "").lower()

                if effective_cat in ("direct_identifier", "sensitive_attribute"):
                    if "iban" in pii_type or "iban" in col.lower():
                        page_df[col] = page_df[col].apply(mask_iban)
                    elif "national_id" in pii_type or "ssn" in col.lower() or "national" in col.lower():
                        page_df[col] = page_df[col].apply(mask_national_id)
                    elif "card" in pii_type or "pan" in col.lower():
                        page_df[col] = page_df[col].apply(lambda v: mask_card_number(v, "bin"))
                    elif "email" in pii_type or "email" in col.lower():
                        page_df[col] = page_df[col].apply(mask_email)
                    elif "phone" in pii_type or "mobile" in col.lower():
                        page_df[col] = page_df[col].apply(mask_phone)
                    elif effective_cat == "direct_identifier":
                        page_df[col] = page_df[col].apply(mask_full)
                    elif effective_cat == "sensitive_attribute":
                        # Partial mask for sensitive attributes in raw preview
                        page_df[col] = page_df[col].apply(mask_partial)

        records = [
            {
                k: (
                    None
                    if (v is None or pd.isna(v))
                    else int(v)
                    if isinstance(v, np.integer)
                    else float(v)
                    if isinstance(v, np.floating)
                    else bool(v)
                    if isinstance(v, (np.bool_, bool))
                    else v
                )
                for k, v in row.items()
            }
            for row in page_df.to_dict(orient="records")
        ]

        return {
            "dataset_id": clean_id,
            "page": page,
            "size": size,
            "total_records": total_records,
            "total_pages": total_pages,
            "columns": list(df.columns),
            "records": records,
        }

    @classmethod
    def get_dataset_profiles(cls, dataset_id: str) -> List[ColumnProfile]:
        """Retrieves active column profiles including overrides."""
        clean_id = validate_uuid_id(dataset_id)
        rows = DatabaseRepository.get_column_metadata(clean_id)
        if not rows:
            # Re-run discovery if not already populated
            df = cls.get_dataset_df(clean_id)
            profiles = discover_dataset(df)
            DatabaseRepository.save_column_metadata(
                clean_id, [p.model_dump() for p in profiles]
            )
            return profiles

        profiles: List[ColumnProfile] = []
        for r in rows:
            profiles.append(
                ColumnProfile(
                    column_name=r["column_name"],
                    detected_type=r["inferred_category"],
                    specific_type=r["detected_pii_type"],
                    confidence=float(r["confidence_score"]),
                    explanation="; ".join(r.get("detection_reasons", []))
                    if isinstance(r.get("detection_reasons"), list)
                    else str(r.get("detection_reasons")),
                    sample_values_masked=["[MASKED]"],
                    unique_count=0,
                    null_count=0,
                    is_overridden=bool(r.get("is_overridden")),
                    user_category=r.get("user_category"),
                )
            )
        return profiles

    @classmethod
    def update_overrides(
        cls, dataset_id: str, overrides: List[ColumnOverrideItem]
    ) -> List[ColumnProfile]:
        """Saves user classification overrides to SQLite and returns updated profiles."""
        clean_id = validate_uuid_id(dataset_id)
        override_dicts = [ov.model_dump() for ov in overrides]
        DatabaseRepository.update_column_overrides(clean_id, override_dicts)
        DatabaseRepository.log_audit(
            action="update_overrides",
            dataset_id=clean_id,
            details={"overrides_count": len(overrides)},
        )
        return cls.get_dataset_profiles(clean_id)
