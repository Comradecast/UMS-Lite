import pytest
from transparencyx.parse.sections import Section
from transparencyx.normalize.assets import extract_asset_candidates, insert_normalized_assets, process_assets_for_disclosure
from transparencyx.db.database import get_connection, initialize_database


def test_extract_asset_candidates_success():
    raw_text = """
    Some random text at the top
    Apple Inc Stock   $1,001 - $15,000
    Random row that should be ignored
    Google Corp       Over $50,000,000
    Treasury Bonds    None
    Checking Account  N/A
    """
    section = Section(name="ASSETS", start_index=0, end_index=100, raw_text=raw_text)

    candidates = extract_asset_candidates(section)

    assert len(candidates) == 4

    assert candidates[0].asset_name == "Apple Inc Stock"
    assert candidates[0].original_value_range == "$1,001 - $15,000"

    assert candidates[1].asset_name == "Google Corp"
    assert candidates[1].original_value_range == "Over $50,000,000"

    assert candidates[2].asset_name == "Treasury Bonds"
    assert candidates[2].original_value_range == "None"

    assert candidates[3].asset_name == "Checking Account"
    assert candidates[3].original_value_range == "N/A"

def test_extract_asset_candidates_wrong_section():
    raw_text = "Apple Inc Stock   $1,001 - $15,000"
    section = Section(name="INCOME", start_index=0, end_index=100, raw_text=raw_text)

    candidates = extract_asset_candidates(section)
    assert len(candidates) == 0

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)

    # We need a dummy politician and raw_disclosure to satisfy foreign keys
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        now = "2023-01-01T00:00:00Z"

        cursor.execute("""
            INSERT INTO politicians (first_name, last_name, full_name, chamber, created_at, updated_at)
            VALUES ('John', 'Doe', 'John Doe', 'house', ?, ?)
        """, (now, now))
        pol_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO raw_disclosures (politician_id, source_chamber, source_name, filing_year, retrieved_at, raw_metadata_json, created_at)
            VALUES (?, 'house', 'test', 2023, ?, '{}', ?)
        """, (pol_id, now, now))
        raw_id = cursor.lastrowid

    return db_path, pol_id, raw_id

def test_insert_normalized_assets(test_db):
    db_path, pol_id, raw_id = test_db

    raw_text = """
    Apple Inc Stock   $1,001 - $15,000
    Missing bounds    $100 to $200
    """
    section = Section(name="ASSETS", start_index=0, end_index=100, raw_text=raw_text)
    candidates = extract_asset_candidates(section)

    inserted = insert_normalized_assets(db_path, raw_id, pol_id, candidates)

    # Missing bounds won't fail closed if range parser handles it by returning Nones,
    # it still inserts what it can.
    assert inserted == 2

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM normalized_assets ORDER BY id ASC")
        rows = cursor.fetchall()

        assert len(rows) == 2

        assert rows[0]["asset_name"] == "Apple Inc Stock"
        assert rows[0]["original_value_range"] == "$1,001 - $15,000"
        assert rows[0]["value_min"] == 1001
        assert rows[0]["value_max"] == 15000

        assert rows[1]["asset_name"] == "Missing bounds"
        assert rows[1]["value_min"] is None

def test_process_assets_pipeline(test_db):
    db_path, pol_id, raw_id = test_db

    full_text = """
    Header info

    ASSETS
    Asset 1  $1,001 - $15,000
    Asset 2  Over $50,000,000

    INCOME
    Income 1  $1,001 - $15,000
    """

    inserted = process_assets_for_disclosure(db_path, raw_id, pol_id, full_text)
    assert inserted == 2

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT asset_name FROM normalized_assets")
        names = [row["asset_name"] for row in cursor.fetchall()]

        assert "Asset 1" in names
        assert "Asset 2" in names
        assert "Income 1" not in names
