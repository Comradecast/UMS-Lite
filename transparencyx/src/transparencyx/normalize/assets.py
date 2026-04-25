"""
Normalization module for financial assets.
"""
import datetime
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

from transparencyx.parse.sections import Section, detect_sections
from transparencyx.ranges import parse_range
from transparencyx.db.database import get_connection

@dataclass
class AssetCandidate:
    """
    Represents an unparsed, deterministic asset candidate extracted from raw text.
    """
    raw_line: str
    asset_name: str
    original_value_range: Optional[str]


def extract_asset_candidates(section: Section) -> List[AssetCandidate]:
    """
    Extracts deterministic asset candidates from a section labeled 'ASSETS'.
    Only identifies lines containing range indicators like '$', 'Over', 'None', 'N/A'.
    """
    if section.name != "ASSETS":
        return []

    candidates = []
    lines = section.raw_text.split("\n")

    for line in lines:
        raw_line = line.strip()
        if not raw_line:
            continue

        # Detect simple value range markers.
        lower_line = raw_line.lower()
        has_dollar = "$" in raw_line
        has_over = "over $" in lower_line
        has_none = "none" in lower_line.split()  # Exact word match to avoid substring false positives
        has_na = "n/a" in lower_line.split()

        if has_dollar or has_over or has_none or has_na:
            # Determine split point for asset_name
            split_idx = -1

            if has_dollar:
                split_idx = raw_line.find("$")
                # Handle "Over $"
                if "over" in lower_line and split_idx > 4:
                    if raw_line[split_idx-5:split_idx].lower() == "over ":
                        split_idx -= 5
            elif has_none:
                # Find where the word "None" or "none" is
                split_idx = lower_line.find("none")
            elif has_na:
                split_idx = lower_line.find("n/a")

            if split_idx != -1:
                asset_name = raw_line[:split_idx].strip()
                range_str = raw_line[split_idx:].strip()

                # If there's no asset name before the value, it's likely a malformed/continued line
                if asset_name:
                    candidates.append(AssetCandidate(
                        raw_line=raw_line,
                        asset_name=asset_name,
                        original_value_range=range_str
                    ))

    return candidates


def insert_normalized_assets(
    db_path: Path,
    raw_disclosure_id: int,
    politician_id: int,
    candidates: List[AssetCandidate]
) -> int:
    """
    Inserts a list of valid AssetCandidates into the normalized_assets table.
    Returns the number of rows inserted.
    """
    inserted_count = 0
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        for candidate in candidates:
            # Fail closed: skip if no value range
            if not candidate.original_value_range:
                continue

            # Parse the range
            parsed_range = parse_range(candidate.original_value_range)

            cursor.execute(
                """
                INSERT INTO normalized_assets (
                    raw_disclosure_id,
                    politician_id,
                    asset_name,
                    asset_category,
                    original_value_range,
                    value_min,
                    value_max,
                    value_midpoint,
                    confidence,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_disclosure_id,
                    politician_id,
                    candidate.asset_name,
                    "unknown",  # per requirements
                    parsed_range.original_label,
                    parsed_range.minimum,
                    parsed_range.maximum,
                    parsed_range.midpoint,
                    "low",      # per requirements
                    now
                )
            )
            inserted_count += 1

    return inserted_count


def process_assets_for_disclosure(
    db_path: Path,
    raw_disclosure_id: int,
    politician_id: int,
    extracted_text: str
) -> int:
    """
    Pipeline function to detect sections, find ASSETS, extract candidates, and insert them.
    Returns the number of inserted assets.
    """
    sections = detect_sections(extracted_text)

    inserted = 0
    for section in sections:
        if section.name == "ASSETS":
            candidates = extract_asset_candidates(section)
            if candidates:
                inserted += insert_normalized_assets(
                    db_path=db_path,
                    raw_disclosure_id=raw_disclosure_id,
                    politician_id=politician_id,
                    candidates=candidates
                )

    return inserted
