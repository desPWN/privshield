"""
FinGuard Application Configuration & Path Management
"""

import os
from pathlib import Path
from typing import List


class Settings:
    PROJECT_NAME: str = "PrivShield"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    APP_DIR: Path = BASE_DIR / "app"
    DATA_DIR: Path = BASE_DIR / "data"
    STORAGE_DIR: Path = BASE_DIR / "storage"
    RAW_STORAGE_DIR: Path = STORAGE_DIR / "raw"
    ANONYMIZED_STORAGE_DIR: Path = STORAGE_DIR / "anonymized"
    REPORTS_STORAGE_DIR: Path = STORAGE_DIR / "reports"

    # Persistence
    DB_PATH: Path = DATA_DIR / "finguard.db"
    DEMO_DATASET_PATH: Path = DATA_DIR / "jordan_financial_transactions.csv"

    # File uploads
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: set = {".csv", ".xlsx", ".json"}

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    def __init__(self):
        # Ensure directories exist
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.RAW_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.ANONYMIZED_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.REPORTS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
