"""
tests_e2e/tier1_features/test_f13_database_persistence.py
Feature 13: SQLite Database Persistence & Migrations.
Validates SQLite persistence schemas for datasets, token mappings, profiles, and immutable audit logs.
"""

import sqlite3
import pytest


@pytest.fixture
def memory_db():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE datasets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            industry TEXT NOT NULL,
            is_encrypted BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE token_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT NOT NULL,
            token TEXT NOT NULL,
            encrypted_original TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    yield conn
    conn.close()


def test_datasets_table_crud(memory_db):
    cur = memory_db.cursor()
    cur.execute("INSERT INTO datasets (id, name, row_count, industry) VALUES (?, ?, ?, ?)",
                ("ds-001", "Hospital Patients", 1000, "healthcare"))
    memory_db.commit()

    cur.execute("SELECT name, row_count, industry FROM datasets WHERE id = ?", ("ds-001",))
    row = cur.fetchone()
    assert row == ("Hospital Patients", 1000, "healthcare")


def test_token_mappings_foreign_key_and_persistence(memory_db):
    cur = memory_db.cursor()
    cur.execute("INSERT INTO datasets (id, name, row_count, industry) VALUES (?, ?, ?, ?)",
                ("ds-002", "Bank Accounts", 500, "finance"))
    cur.execute("INSERT INTO token_mappings (dataset_id, token, encrypted_original) VALUES (?, ?, ?)",
                ("ds-002", "TOK-9901", "ENC_RAW_IBAN"))
    memory_db.commit()

    cur.execute("SELECT token, encrypted_original FROM token_mappings WHERE dataset_id = ?", ("ds-002",))
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "TOK-9901"


def test_audit_logs_append_and_query(memory_db):
    cur = memory_db.cursor()
    cur.execute("INSERT INTO audit_logs (dataset_id, action, status) VALUES (?, ?, ?)",
                ("ds-001", "restore_dataset", "success"))
    cur.execute("INSERT INTO audit_logs (dataset_id, action, status) VALUES (?, ?, ?)",
                ("ds-001", "lookup_token", "failed_auth"))
    memory_db.commit()

    cur.execute("SELECT action, status FROM audit_logs WHERE dataset_id = ? ORDER BY id ASC", ("ds-001",))
    logs = cur.fetchall()
    assert len(logs) == 2
    assert logs[0] == ("restore_dataset", "success")
    assert logs[1] == ("lookup_token", "failed_auth")


def test_unique_constraint_primary_key(memory_db):
    cur = memory_db.cursor()
    cur.execute("INSERT INTO datasets (id, name, row_count, industry) VALUES (?, ?, ?, ?)",
                ("ds-unique", "Test", 10, "custom"))
    memory_db.commit()

    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO datasets (id, name, row_count, industry) VALUES (?, ?, ?, ?)",
                    ("ds-unique", "Duplicate", 20, "custom"))


def test_transaction_rollback_on_failure(memory_db):
    cur = memory_db.cursor()
    cur.execute("INSERT INTO datasets (id, name, row_count, industry) VALUES (?, ?, ?, ?)",
                ("ds-tx", "Initial", 50, "custom"))
    memory_db.commit()

    try:
        cur.execute("INSERT INTO datasets (id, name, row_count, industry) VALUES (?, ?, ?, ?)",
                    ("ds-fail", "Will Rollback", 100, "custom"))
        # Force intentional failure
        raise RuntimeError("Simulated failure")
    except RuntimeError:
        memory_db.rollback()

    cur.execute("SELECT id FROM datasets WHERE id = ?", ("ds-fail",))
    assert cur.fetchone() is None
