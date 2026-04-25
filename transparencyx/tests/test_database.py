import pytest
import sqlite3
from transparencyx.db.database import get_connection, initialize_database


def test_initialize_database(tmp_path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    assert db_path.exists()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Verify tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row["name"] for row in cursor.fetchall()}

        assert "politicians" in tables
        assert "raw_disclosures" in tables
        assert "normalized_assets" in tables
        assert "trades" in tables

        # Verify indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = {row["name"] for row in cursor.fetchall()}

        assert "idx_raw_disclosures_source_chamber_year" in indexes
        assert "idx_raw_disclosures_source_hash" in indexes
        assert "idx_politicians_full_name" in indexes
        assert "idx_normalized_assets_politician_id" in indexes
        assert "idx_trades_politician_id" in indexes


def test_foreign_keys_enabled(tmp_path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys;")
        fk_status = cursor.fetchone()[0]
        assert fk_status == 1
