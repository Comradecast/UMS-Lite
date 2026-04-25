"""
SQLite database schema definition.
"""

def get_schema_sql() -> str:
    """
    Returns the SQL schema for creating the database tables and indexes.
    """
    return """
    CREATE TABLE IF NOT EXISTS politicians (
        id INTEGER PRIMARY KEY,
        bioguide_id TEXT UNIQUE NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        full_name TEXT NOT NULL,
        chamber TEXT NOT NULL,
        state TEXT NULL,
        district TEXT NULL,
        party TEXT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS raw_disclosures (
        id INTEGER PRIMARY KEY,
        politician_id INTEGER NULL,
        source_chamber TEXT NOT NULL,
        source_name TEXT NOT NULL,
        filing_year INTEGER NOT NULL,
        filing_type TEXT NULL,
        document_title TEXT NULL,
        document_url TEXT NULL,
        local_path TEXT NULL,
        source_hash TEXT NULL UNIQUE,
        retrieved_at TEXT NOT NULL,
        raw_metadata_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (politician_id) REFERENCES politicians(id)
    );

    CREATE TABLE IF NOT EXISTS normalized_assets (
        id INTEGER PRIMARY KEY,
        raw_disclosure_id INTEGER NOT NULL,
        politician_id INTEGER NOT NULL,
        asset_name TEXT NOT NULL,
        asset_category TEXT NOT NULL,
        original_value_range TEXT NOT NULL,
        value_min INTEGER NULL,
        value_max INTEGER NULL,
        value_midpoint INTEGER NULL,
        income_range TEXT NULL,
        income_min INTEGER NULL,
        income_max INTEGER NULL,
        income_midpoint INTEGER NULL,
        confidence TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (raw_disclosure_id) REFERENCES raw_disclosures(id),
        FOREIGN KEY (politician_id) REFERENCES politicians(id)
    );

    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY,
        politician_id INTEGER NOT NULL,
        raw_disclosure_id INTEGER NULL,
        transaction_date TEXT NULL,
        disclosure_date TEXT NULL,
        asset_name TEXT NOT NULL,
        ticker TEXT NULL,
        transaction_type TEXT NOT NULL,
        original_amount_range TEXT NOT NULL,
        amount_min INTEGER NULL,
        amount_max INTEGER NULL,
        amount_midpoint INTEGER NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (politician_id) REFERENCES politicians(id),
        FOREIGN KEY (raw_disclosure_id) REFERENCES raw_disclosures(id)
    );

    CREATE INDEX IF NOT EXISTS idx_raw_disclosures_source_chamber_year ON raw_disclosures(source_chamber, filing_year);
    CREATE INDEX IF NOT EXISTS idx_raw_disclosures_source_hash ON raw_disclosures(source_hash);
    CREATE INDEX IF NOT EXISTS idx_politicians_full_name ON politicians(full_name);
    CREATE INDEX IF NOT EXISTS idx_normalized_assets_politician_id ON normalized_assets(politician_id);
    CREATE INDEX IF NOT EXISTS idx_trades_politician_id ON trades(politician_id);
    """
