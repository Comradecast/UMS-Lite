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
    cleaned_name: str
    original_value_range: Optional[str]
    value_range_text: Optional[str]


def clean_asset_name(raw_name: str) -> str:
    """
    Cleans an asset name deterministically without guessing or inference.
    - Strips leading/trailing whitespace
    - Collapses multiple spaces
    - Removes trailing dashes or colons
    - Restrips
    """
    # Collapse whitespace and strip
    cleaned = " ".join(raw_name.split())

    # Remove trailing punctuation
    while cleaned.endswith("-") or cleaned.endswith(":") or cleaned.endswith(" "):
        cleaned = cleaned[:-1].strip()

    return cleaned


def extract_asset_candidates(section: Section) -> List[AssetCandidate]:
    """
    Extracts deterministic asset candidates from a section labeled 'ASSETS'.
    Only identifies lines containing range indicators like '$' or 'Over $'.
    """
    if section.name != "ASSETS":
        return []

    candidates = []
    lines = section.raw_text.split("\n")

    seen = set()

    for line in lines:
        raw_line = line.strip()
        # Collapse whitespace for the line before processing so range matching is clean,
        # but the prompt said "split raw_text into lines, normalize whitespace per line"
        raw_line = " ".join(raw_line.split())

        if not raw_line:
            continue

        lower_line = raw_line.lower()

        # Only line containing "Over $" or "$" are valid
        split_idx = -1

        if "over $" in lower_line:
            # Range starts at "Over $"
            # Need to find the exact case-preserving index of "over $"
            split_idx = lower_line.find("over $")
        elif "$" in lower_line:
            split_idx = lower_line.find("$")

        if split_idx != -1:
            asset_name = raw_line[:split_idx].strip()
            range_str = raw_line[split_idx:].strip()

            cleaned_name = clean_asset_name(asset_name)

            if cleaned_name and range_str:
                # Deduplicate candidates in memory
                key = (cleaned_name, range_str)
                if key not in seen:
                    seen.add(key)
                    candidates.append(AssetCandidate(
                        raw_line=raw_line,
                        asset_name=asset_name,
                        cleaned_name=cleaned_name,
                        original_value_range=range_str,
                        value_range_text=range_str
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

        # Build deduplication set from existing DB records for this raw_disclosure_id
        cursor.execute(
            """
            SELECT asset_name, original_value_range
            FROM normalized_assets
            WHERE raw_disclosure_id = ?
            """,
            (raw_disclosure_id,)
        )
        existing_assets = set((row["asset_name"], row["original_value_range"]) for row in cursor.fetchall())

        for candidate in candidates:
            # Fail closed: skip if no value range or no cleaned name
            if not candidate.value_range_text or not candidate.cleaned_name:
                continue

            # Prevent duplicate inserts
            key = (candidate.cleaned_name, candidate.value_range_text)
            if key in existing_assets:
                continue

            # Parse the range
            parsed_range = parse_range(candidate.value_range_text)

            # Confidence rules
            confidence = "low"
            if candidate.cleaned_name and (parsed_range.minimum is not None or parsed_range.maximum is not None or parsed_range.midpoint is not None):
                confidence = "medium"

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
                    candidate.cleaned_name,
                    "unknown",  # per requirements
                    parsed_range.original_label,
                    parsed_range.minimum,
                    parsed_range.maximum,
                    parsed_range.midpoint,
                    confidence,
                    now
                )
            )
            existing_assets.add(key)
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
