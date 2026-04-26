import pytest
from transparencyx.db.database import get_connection, initialize_database
from transparencyx.ingest.house import HouseDisclosureRecord, compute_source_hash, insert_house_raw_disclosure

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)
    return db_path

def test_compute_source_hash():
    record1 = HouseDisclosureRecord(
        filing_year=2023,
        document_title="Report 1",
        document_url="http://example.com/1",
        politician_name="Doe, John"
    )

    record2 = HouseDisclosureRecord(
        filing_year=2023,
        document_title="Report 1",
        document_url="http://example.com/1",
        politician_name="Doe, John"
    )

    record3 = HouseDisclosureRecord(
        filing_year=2024, # Different year
        document_title="Report 1",
        document_url="http://example.com/1",
        politician_name="Doe, John"
    )

    # Hashes should be deterministic
    hash1 = compute_source_hash(record1)
    hash2 = compute_source_hash(record2)
    hash3 = compute_source_hash(record3)

    assert hash1 == hash2
    assert hash1 != hash3

def test_insert_house_raw_disclosure(test_db):
    record = HouseDisclosureRecord(
        filing_year=2023,
        document_title="Financial Disclosure",
        document_url="http://example.com/fd.pdf",
        politician_name="Doe, John",
        filing_type="Annual",
        local_path="data/raw/house/2023/fd.pdf"
    )

    # First insert
    record_id = insert_house_raw_disclosure(test_db, record)
    assert record_id == 1

    # Verify in DB
    with get_connection(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM raw_disclosures WHERE id = ?", (record_id,))
        row = cursor.fetchone()

        assert row is not None
        assert row["source_chamber"] == "house"
        assert row["source_name"] == "House Financial Disclosure"
        assert row["filing_year"] == 2023
        assert row["document_title"] == "Financial Disclosure"
        assert row["document_url"] == "http://example.com/fd.pdf"
        assert row["local_path"] == "data/raw/house/2023/fd.pdf"
        assert row["source_hash"] == compute_source_hash(record)

def test_insert_prevents_duplicates(test_db):
    record = HouseDisclosureRecord(
        filing_year=2023,
        document_title="Financial Disclosure",
        document_url="http://example.com/fd.pdf",
        politician_name="Doe, John"
    )

    # First insert
    id1 = insert_house_raw_disclosure(test_db, record)

    # Second insert with exactly same data
    id2 = insert_house_raw_disclosure(test_db, record)

    assert id1 == id2

    # Verify only one row exists
    with get_connection(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM raw_disclosures")
        count = cursor.fetchone()[0]
        assert count == 1

def test_cli_ingest_commands(tmp_path, monkeypatch, capsys):
    import sys
    import json
    from unittest.mock import patch
    from transparencyx.cli import main

    db_path = tmp_path / "test.sqlite"

    # Test DB init
    test_args_init = ["transparencyx", "db", "init", "--path", str(db_path)]
    with patch.object(sys, 'argv', test_args_init):
        main()

    captured = capsys.readouterr()
    assert "Database initialized" in captured.out
    assert db_path.exists()

    # Test House ingest sample
    test_args_ingest = ["transparencyx", "ingest", "house-sample", "--db", str(db_path)]
    with patch.object(sys, 'argv', test_args_ingest):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["success"] is True
    assert output["record_id"] == 1
