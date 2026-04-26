"""
Raw ingestion logic for House Financial Disclosures.
"""
import sqlite3
import hashlib
import json
import datetime
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path

from transparencyx.db.database import get_connection


@dataclass
class HouseDisclosureRecord:
    """
    Represents a raw House disclosure record to be ingested.
    """
    filing_year: int
    document_title: str
    document_url: str
    politician_name: str  # Kept in metadata for now since we aren't linking to politicians table yet
    filing_type: Optional[str] = None
    local_path: Optional[str] = None


def compute_source_hash(record: HouseDisclosureRecord) -> str:
    """
    Computes a deterministic SHA256 hash for a House disclosure record to prevent duplicates.
    """
    # Create a stable string representation of the core fields
    stable_string = f"house|{record.filing_year}|{record.document_title}|{record.document_url}"
    return hashlib.sha256(stable_string.encode('utf-8')).hexdigest()


def insert_house_raw_disclosure(db_path: Path, record: HouseDisclosureRecord) -> int:
    """
    Inserts a House disclosure record into the raw_disclosures table.
    Checks for duplicates using the source_hash and returns the existing ID if found.
    """
    source_hash = compute_source_hash(record)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Check for existing record
        cursor.execute(
            "SELECT id FROM raw_disclosures WHERE source_hash = ?",
            (source_hash,)
        )
        existing = cursor.fetchone()
        if existing:
            return existing["id"]

        # Prepare insertion data
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # We store the raw data as JSON for auditability and future extraction
        raw_metadata_json = json.dumps(asdict(record))

        cursor.execute(
            """
            INSERT INTO raw_disclosures (
                source_chamber,
                source_name,
                filing_year,
                filing_type,
                document_title,
                document_url,
                local_path,
                source_hash,
                retrieved_at,
                raw_metadata_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "house",
                "House Financial Disclosure",
                record.filing_year,
                record.filing_type,
                record.document_title,
                record.document_url,
                record.local_path,
                source_hash,
                now,  # retrieved_at
                raw_metadata_json,
                now   # created_at
            )
        )

        return cursor.lastrowid
