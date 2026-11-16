"""
PrivShield Application Services Module
Exports core services for:
- Dataset ingestion & safe preview (DatasetService)
- Mathematical anonymization & metrics (AnonymizationService)
- Cryptographic vault & authenticated encryption (EncryptionService)
- Pre-built multi-industry dataset profiles (ProfileService)
- Multi-industry realistic synthetic data generators (synthetic_data_service)
- Secure recovery & reversible pseudonymization (RecoveryService)
- Sanitized multi-format export (ExportService / export_dataset)
- Publication-grade ReportLab PDF generation (pdf_service / generate_pdf_report)
"""

from backend.app.services.anonymization_service import AnonymizationService
from backend.app.services.dataset_service import DatasetService
from backend.app.services.encryption_service import EncryptionService
from backend.app.services.export_service import export_dataset, sanitize_csv_cell
from backend.app.services.pdf_service import generate_pdf_report
from backend.app.services.profile_service import ProfileService
from backend.app.services.recovery_service import RecoveryService
from backend.app.services.synthetic_data_service import (
    generate_bank_transactions_dataset,
    generate_customer_database_dataset,
    generate_employee_records_dataset,
    generate_hospital_dataset,
    generate_industry_dataset,
    generate_university_students_dataset,
    save_synthetic_datasets,
)

__all__ = [
    "DatasetService",
    "AnonymizationService",
    "EncryptionService",
    "ProfileService",
    "RecoveryService",
    "generate_hospital_dataset",
    "generate_bank_transactions_dataset",
    "generate_university_students_dataset",
    "generate_employee_records_dataset",
    "generate_customer_database_dataset",
    "generate_industry_dataset",
    "save_synthetic_datasets",
    "export_dataset",
    "sanitize_csv_cell",
    "generate_pdf_report",
]
