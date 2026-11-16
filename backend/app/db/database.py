"""
FinGuard SQLite Persistence Layer
Manages database initialization, WAL mode, migrations, and CRUD operations for:
- Datasets
- Column metadata & discovery classifications
- Anonymization runs & metrics
- Presets
- Immutable audit logs
"""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional
from backend.app.core.config import settings

_db_lock = threading.Lock()

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    filename TEXT NOT NULL,
    format TEXT NOT NULL CHECK(format IN ('csv', 'xlsx', 'json')),
    file_size_bytes INTEGER NOT NULL,
    row_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    raw_storage_path TEXT NOT NULL,
    industry_profile TEXT DEFAULT 'finance',
    is_encrypted INTEGER DEFAULT 0,
    encryption_algorithm TEXT DEFAULT 'AES-256-GCM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS column_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    column_name TEXT NOT NULL,
    column_index INTEGER NOT NULL,
    data_type TEXT NOT NULL,
    inferred_category TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    detected_pii_type TEXT NOT NULL,
    detection_reasons TEXT NOT NULL,
    is_overridden INTEGER DEFAULT 0,
    user_category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    UNIQUE(dataset_id, column_name)
);

CREATE TABLE IF NOT EXISTS anonymization_runs (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    config_json TEXT NOT NULL,
    anonymized_storage_path TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'failed')),
    processing_mode TEXT DEFAULT 'irreversible_anonymization',
    is_reversible INTEGER DEFAULT 0,
    token_mapping_count INTEGER DEFAULT 0,
    records_input INTEGER NOT NULL,
    records_retained INTEGER NOT NULL,
    records_suppressed INTEGER NOT NULL,
    suppression_rate REAL NOT NULL,
    achieved_k INTEGER NOT NULL,
    achieved_l INTEGER,
    achieved_t REAL,
    utility_retention_score REAL NOT NULL,
    metrics_json TEXT,
    execution_time_ms REAL NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS anonymization_presets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    rules_json TEXT NOT NULL,
    is_system_preset INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS industry_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT NOT NULL,
    suggested_rules_json TEXT NOT NULL,
    is_built_in INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS token_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    column_name TEXT NOT NULL,
    row_index INTEGER NOT NULL,
    token TEXT NOT NULL,
    encrypted_original_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recovery_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    run_id TEXT,
    actor TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    action TEXT NOT NULL,
    token_queried TEXT,
    records_recovered INTEGER NOT NULL,
    justification TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    dataset_id TEXT,
    run_id TEXT,
    actor TEXT DEFAULT 'local_user',
    details_json TEXT NOT NULL,
    ip_address TEXT DEFAULT '127.0.0.1',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_col_meta_dataset ON column_metadata(dataset_id);
CREATE INDEX IF NOT EXISTS idx_runs_dataset ON anonymization_runs(dataset_id);
CREATE INDEX IF NOT EXISTS idx_tokens_lookup ON token_mappings(run_id, column_name, token);
CREATE INDEX IF NOT EXISTS idx_tokens_token_only ON token_mappings(token);
CREATE INDEX IF NOT EXISTS idx_tokens_dataset ON token_mappings(dataset_id);
CREATE INDEX IF NOT EXISTS idx_recovery_audit_timestamp ON recovery_audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
"""

DEFAULT_PRESETS = [
    {
        "id": "preset_cbj_strict",
        "name": "Strict Banking Secrecy (CBJ / GDPR)",
        "description": "High privacy threshold: Strict K=5, Distinct L=3, T=0.15 with maximum 10% suppression budget.",
        "rules_json": json.dumps({
            "k_metric": 5,
            "l_metric": 3,
            "t_metric": 0.15,
            "max_suppression_pct": 0.10,
            "suppression_strategy": "record",
            "masking_rules": {
                "National_ID": "mask_national_id",
                "IBAN": "mask_iban",
                "Card_Number": "mask_card",
                "Customer_Name": "mask_full",
                "Email": "mask_email",
                "Phone": "mask_phone"
            },
            "generalization_levels": {
                "City": 1,
                "Customer_Age": 1,
                "Amount": 1,
                "Timestamp": 1
            }
        }),
        "is_system_preset": 1
    },
    {
        "id": "preset_research_balanced",
        "name": "Balanced Research Sharing",
        "description": "Balanced privacy-utility trade-off: K=3, L=2, T=0.25 with 20% suppression budget.",
        "rules_json": json.dumps({
            "k_metric": 3,
            "l_metric": 2,
            "t_metric": 0.25,
            "max_suppression_pct": 0.20,
            "suppression_strategy": "record",
            "masking_rules": {
                "National_ID": "mask_national_id",
                "IBAN": "mask_iban",
                "Customer_Name": "mask_full",
                "Email": "mask_email"
            },
            "generalization_levels": {
                "City": 1,
                "Customer_Age": 1
            }
        }),
        "is_system_preset": 1
    },
    {
        "id": "preset_high_utility",
        "name": "High Utility Open Release",
        "description": "Prioritizes record retention: K=2 without L or T constraints and low generalization.",
        "rules_json": json.dumps({
            "k_metric": 2,
            "l_metric": None,
            "t_metric": None,
            "max_suppression_pct": 0.05,
            "suppression_strategy": "record",
            "masking_rules": {
                "National_ID": "mask_national_id",
                "IBAN": "mask_iban",
                "Customer_Name": "mask_full"
            },
            "generalization_levels": {
                "City": 1
            }
        }),
        "is_system_preset": 1
    }
]


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a SQLite connection configured with WAL mode and row factory."""
    target_path = db_path or settings.DB_PATH
    conn = sqlite3.connect(
        str(target_path),
        check_same_thread=False,
        timeout=30.0
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db():
    """Context manager providing transactional connection management."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """Initializes tables, indexes, and default presets."""
    with _db_lock:
        target_path = db_path or settings.DB_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(target_path)
        try:
            conn.executescript(SCHEMA_SQL)
            cursor = conn.cursor()

            # Dynamic migration for existing databases
            cursor.execute("PRAGMA table_info(datasets);")
            ds_cols = {row["name"] for row in cursor.fetchall()}
            if "industry_profile" not in ds_cols:
                cursor.execute("ALTER TABLE datasets ADD COLUMN industry_profile TEXT DEFAULT 'finance'")
            if "is_encrypted" not in ds_cols:
                cursor.execute("ALTER TABLE datasets ADD COLUMN is_encrypted INTEGER DEFAULT 0")
            if "encryption_algorithm" not in ds_cols:
                cursor.execute("ALTER TABLE datasets ADD COLUMN encryption_algorithm TEXT DEFAULT 'AES-256-GCM'")

            cursor.execute("PRAGMA table_info(anonymization_runs);")
            run_cols = {row["name"] for row in cursor.fetchall()}
            if "processing_mode" not in run_cols:
                cursor.execute("ALTER TABLE anonymization_runs ADD COLUMN processing_mode TEXT DEFAULT 'irreversible_anonymization'")
            if "is_reversible" not in run_cols:
                cursor.execute("ALTER TABLE anonymization_runs ADD COLUMN is_reversible INTEGER DEFAULT 0")
            if "token_mapping_count" not in run_cols:
                cursor.execute("ALTER TABLE anonymization_runs ADD COLUMN token_mapping_count INTEGER DEFAULT 0")

            # Insert default presets if not already present
            for preset in DEFAULT_PRESETS:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO anonymization_presets (id, name, description, rules_json, is_system_preset)
                    VALUES (:id, :name, :description, :rules_json, :is_system_preset)
                    """,
                    preset
                )
            conn.commit()
        finally:
            conn.close()


class DatabaseRepository:
    """Repository class encapsulating SQLite operations for FinGuard."""

    @staticmethod
    def create_dataset(data: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "id": data["id"],
            "name": data["name"],
            "filename": data["filename"],
            "format": data["format"],
            "file_size_bytes": data["file_size_bytes"],
            "row_count": data["row_count"],
            "column_count": data["column_count"],
            "raw_storage_path": data["raw_storage_path"],
            "industry_profile": data.get("industry_profile", "finance"),
            "is_encrypted": data.get("is_encrypted", 0),
            "encryption_algorithm": data.get("encryption_algorithm", "AES-256-GCM"),
        }
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO datasets (
                    id, name, filename, format, file_size_bytes, row_count, column_count,
                    raw_storage_path, industry_profile, is_encrypted, encryption_algorithm
                ) VALUES (
                    :id, :name, :filename, :format, :file_size_bytes, :row_count, :column_count,
                    :raw_storage_path, :industry_profile, :is_encrypted, :encryption_algorithm
                )
                """,
                payload
            )
            cursor.execute("SELECT * FROM datasets WHERE id = ?", (data["id"],))
            row = cursor.fetchone()
            return dict(row)

    @staticmethod
    def _normalize_dataset_dict(r: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures both frontend-compatible and backend-compatible keys exist."""
        d = dict(r)
        fmt = d.get("format") or d.get("file_format") or "csv"
        fname = d.get("filename") or d.get("original_filename") or ""
        r_cnt = d.get("row_count") if d.get("row_count") is not None else d.get("record_count", 0)
        p_str = d.get("raw_storage_path") or d.get("storage_path") or ""
        name = d.get("name") or fname
        is_synth = 1 if ("demo" in fname.lower() or "demo" in name.lower() or d.get("is_synthetic")) else 0
        d["format"] = fmt
        d["file_format"] = fmt
        d["filename"] = fname
        d["original_filename"] = fname
        d["row_count"] = r_cnt
        d["record_count"] = r_cnt
        d["raw_storage_path"] = p_str
        d["storage_path"] = p_str
        d["is_synthetic"] = is_synth
        d["is_encrypted"] = bool(d.get("is_encrypted", 0))
        d["industry_profile"] = d.get("industry_profile", "finance")
        return d

    @staticmethod
    def get_dataset(dataset_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM datasets WHERE id = ? AND is_deleted = 0",
                (dataset_id,)
            )
            row = cursor.fetchone()
            return DatabaseRepository._normalize_dataset_dict(dict(row)) if row else None

    @staticmethod
    def list_datasets() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM datasets WHERE is_deleted = 0 ORDER BY created_at DESC"
            )
            rows = [dict(r) for r in cursor.fetchall()]
            valid = []
            for r in rows:
                ds_id = r.get("id")
                p_str = r.get("raw_storage_path")
                local_raw = settings.RAW_STORAGE_DIR / f"{ds_id}.csv"
                if local_raw.exists():
                    valid.append(DatabaseRepository._normalize_dataset_dict(r))
                elif p_str and (Path(p_str).exists() or Path(f"{p_str}.enc").exists()):
                    valid.append(DatabaseRepository._normalize_dataset_dict(r))
            return valid

    @staticmethod
    def delete_dataset(dataset_id: str) -> bool:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE datasets SET is_deleted = 1 WHERE id = ?",
                (dataset_id,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def save_column_metadata(dataset_id: str, profiles: List[Dict[str, Any]]) -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM column_metadata WHERE dataset_id = ?", (dataset_id,))
            for idx, p in enumerate(profiles):
                reasons = p.get("explanation", "")
                if isinstance(reasons, str):
                    reasons_json = json.dumps([reasons])
                elif isinstance(reasons, list):
                    reasons_json = json.dumps(reasons)
                else:
                    reasons_json = json.dumps([])

                cursor.execute(
                    """
                    INSERT INTO column_metadata (
                        dataset_id, column_name, column_index, data_type,
                        inferred_category, confidence_score, detected_pii_type,
                        detection_reasons, is_overridden, user_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dataset_id,
                        p["column_name"],
                        idx,
                        p.get("data_type", "string"),
                        p["detected_type"],
                        float(p.get("confidence", 0.0)),
                        p.get("specific_type", "unknown"),
                        reasons_json,
                        1 if p.get("is_overridden") else 0,
                        p.get("user_category")
                    )
                )

    @staticmethod
    def get_column_metadata(dataset_id: str) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM column_metadata
                WHERE dataset_id = ?
                ORDER BY column_index ASC
                """,
                (dataset_id,)
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item["detection_reasons"] = json.loads(item["detection_reasons"])
                except Exception:
                    item["detection_reasons"] = [item["detection_reasons"]]
                results.append(item)
            return results

    @staticmethod
    def update_column_overrides(dataset_id: str, overrides: List[Dict[str, Any]]) -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            for ov in overrides:
                col_name = ov["column_name"]
                cat = ov.get("user_category") or ov.get("category")
                cursor.execute(
                    """
                    UPDATE column_metadata
                    SET is_overridden = 1, user_category = ?
                    WHERE dataset_id = ? AND column_name = ?
                    """,
                    (cat, dataset_id, col_name)
                )

    @staticmethod
    def create_anonymization_run(data: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "id": data["id"],
            "dataset_id": data["dataset_id"],
            "config_json": data["config_json"],
            "anonymized_storage_path": data["anonymized_storage_path"],
            "status": data["status"],
            "processing_mode": data.get("processing_mode", "irreversible_anonymization"),
            "is_reversible": data.get("is_reversible", 0),
            "token_mapping_count": data.get("token_mapping_count", 0),
            "records_input": data["records_input"],
            "records_retained": data["records_retained"],
            "records_suppressed": data["records_suppressed"],
            "suppression_rate": data["suppression_rate"],
            "achieved_k": data["achieved_k"],
            "achieved_l": data.get("achieved_l"),
            "achieved_t": data.get("achieved_t"),
            "utility_retention_score": data["utility_retention_score"],
            "metrics_json": data.get("metrics_json"),
            "execution_time_ms": data["execution_time_ms"],
            "error_message": data.get("error_message"),
        }
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO anonymization_runs (
                    id, dataset_id, config_json, anonymized_storage_path, status,
                    processing_mode, is_reversible, token_mapping_count,
                    records_input, records_retained, records_suppressed, suppression_rate,
                    achieved_k, achieved_l, achieved_t, utility_retention_score,
                    metrics_json, execution_time_ms, error_message
                ) VALUES (
                    :id, :dataset_id, :config_json, :anonymized_storage_path, :status,
                    :processing_mode, :is_reversible, :token_mapping_count,
                    :records_input, :records_retained, :records_suppressed, :suppression_rate,
                    :achieved_k, :achieved_l, :achieved_t, :utility_retention_score,
                    :metrics_json, :execution_time_ms, :error_message
                )
                """,
                payload
            )
            cursor.execute("SELECT * FROM anonymization_runs WHERE id = ?", (data["id"],))
            return dict(cursor.fetchone())

    @staticmethod
    def get_anonymization_run(run_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM anonymization_runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("config_json"):
                try:
                    res["config"] = json.loads(res["config_json"])
                except Exception:
                    res["config"] = {}
            if res.get("metrics_json"):
                try:
                    res["metrics"] = json.loads(res["metrics_json"])
                except Exception:
                    res["metrics"] = {}
            return res

    @staticmethod
    def get_latest_run_for_dataset(dataset_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM anonymization_runs
                WHERE dataset_id = ? AND status = 'completed'
                ORDER BY created_at DESC LIMIT 1
                """,
                (dataset_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return DatabaseRepository.get_anonymization_run(row["id"])

    @staticmethod
    def list_presets() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM anonymization_presets ORDER BY is_system_preset DESC, name ASC")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                p = dict(r)
                try:
                    p["rules"] = json.loads(p["rules_json"])
                except Exception:
                    p["rules"] = {}
                results.append(p)
            return results

    @staticmethod
    def create_preset(data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO anonymization_presets (id, name, description, rules_json, is_system_preset)
                VALUES (:id, :name, :description, :rules_json, :is_system_preset)
                """,
                data
            )
            cursor.execute("SELECT * FROM anonymization_presets WHERE id = ?", (data["id"],))
            res = dict(cursor.fetchone())
            try:
                res["rules"] = json.loads(res["rules_json"])
            except Exception:
                res["rules"] = {}
            return res

    @staticmethod
    def store_token_mappings(dataset_id: str, run_id: str, mappings: List[Dict[str, Any]]) -> int:
        if not mappings:
            return 0
        with get_db() as conn:
            cursor = conn.cursor()
            rows = [
                (
                    dataset_id,
                    run_id,
                    m["column_name"],
                    int(m.get("row_index", 0)),
                    str(m["token"]),
                    str(m["encrypted_original_value"])
                )
                for m in mappings
            ]
            cursor.executemany(
                """
                INSERT INTO token_mappings (dataset_id, run_id, column_name, row_index, token, encrypted_original_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows
            )
            return len(rows)

    @staticmethod
    def lookup_token(token: str, run_id: Optional[str] = None, column_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM token_mappings WHERE token = ?"
            params: List[Any] = [token]
            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)
            if column_name:
                query += " AND column_name = ?"
                params.append(column_name)
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_tokens_for_run(run_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM token_mappings WHERE run_id = ? ORDER BY id ASC LIMIT ?",
                (run_id, limit)
            )
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def count_tokens_for_run(run_id: str) -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM token_mappings WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            return row["cnt"] if row else 0

    @staticmethod
    def count_token_mappings(dataset_id: Optional[str] = None, run_id: Optional[str] = None) -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) as cnt FROM token_mappings WHERE 1=1"
            params: List[Any] = []
            if dataset_id:
                query += " AND dataset_id = ?"
                params.append(dataset_id)
            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return row["cnt"] if row else 0

    @staticmethod
    def log_recovery_audit(
        dataset_id: str,
        actor: str,
        ip_address: str,
        action: str,
        records_recovered: int,
        justification: str,
        run_id: Optional[str] = None,
        token_queried: Optional[str] = None
    ) -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO recovery_audit_logs (
                    dataset_id, run_id, actor, ip_address, action, token_queried, records_recovered, justification
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (dataset_id, run_id, actor, ip_address, action, token_queried, records_recovered, justification)
            )

    @staticmethod
    def get_recovery_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM recovery_audit_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def list_industry_profiles() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM industry_profiles ORDER BY is_built_in DESC, name ASC")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                p = dict(r)
                if p.get("suggested_rules_json"):
                    try:
                        p["suggested_rules"] = json.loads(p["suggested_rules_json"])
                    except Exception:
                        p["suggested_rules"] = {}
                results.append(p)
            return results

    @staticmethod
    def get_industry_profile(profile_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM industry_profiles WHERE id = ?", (profile_id,))
            row = cursor.fetchone()
            if not row:
                return None
            p = dict(row)
            if p.get("suggested_rules_json"):
                try:
                    p["suggested_rules"] = json.loads(p["suggested_rules_json"])
                except Exception:
                    p["suggested_rules"] = {}
            return p

    @staticmethod
    def upsert_industry_profile(data: Dict[str, Any]) -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            rules_json = data.get("suggested_rules_json")
            if not rules_json and "suggested_rules" in data:
                rules_json = json.dumps(data["suggested_rules"])
            cursor.execute(
                """
                INSERT OR REPLACE INTO industry_profiles (
                    id, name, industry, description, icon, suggested_rules_json, is_built_in
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["id"],
                    data["name"],
                    data["industry"],
                    data.get("description", ""),
                    data.get("icon", "Shield"),
                    rules_json or "{}",
                    data.get("is_built_in", 1)
                )
            )

    @staticmethod
    def log_audit(action: str, dataset_id: Optional[str] = None, run_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None, ip_address: str = "127.0.0.1") -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_logs (action, dataset_id, run_id, details_json, ip_address)
                VALUES (?, ?, ?, ?, ?)
                """,
                (action, dataset_id, run_id, json.dumps(details or {}), ip_address)
            )


# Initialize DB on module import
init_db()
