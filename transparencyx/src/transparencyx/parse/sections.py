"""
Section detection and segmentation.
"""
from dataclasses import dataclass
from typing import List


@dataclass
class Section:
    """
    Represents a segmented logical block of text from a disclosure.
    """
    name: str
    start_index: int
    end_index: int
    raw_text: str


# Predefined section markers we look for
KNOWN_HEADERS = [
    "ASSETS",
    "INCOME",
    "LIABILITIES",
    "POSITIONS",
    "AGREEMENTS"
]

def detect_sections(text: str) -> List[Section]:
    """
    Segments raw text into major disclosure sections based on simple keyword detection.
    Does not interpret the content, only segments the raw text block.
    """
    if not text:
        return []

    # Find the positions of all known headers
    found_headers = []
    text_upper = text.upper()

    for header in KNOWN_HEADERS:
        # Simple substring search.
        # This could be improved later (e.g. word boundaries), but keeps things simple for now.
        start_pos = text_upper.find(header)
        if start_pos != -1:
            found_headers.append({
                "name": header,
                "start_index": start_pos
            })

    # If no headers found, return the whole text as "UNCLASSIFIED"
    if not found_headers:
        return [
            Section(
                name="UNCLASSIFIED",
                start_index=0,
                end_index=len(text),
                raw_text=text
            )
        ]

    # Sort found headers by their appearance in the text
    found_headers.sort(key=lambda x: x["start_index"])

    sections = []

    # Process each found header and slice until the next header (or end of text)
    for i, current_header in enumerate(found_headers):
        start_idx = current_header["start_index"]

        # If there's another header after this one, slice up to it
        if i + 1 < len(found_headers):
            end_idx = found_headers[i + 1]["start_index"]
        else:
            # Otherwise, slice to the end of the text
            end_idx = len(text)

        section_text = text[start_idx:end_idx].strip()

        sections.append(
            Section(
                name=current_header["name"],
                start_index=start_idx,
                end_index=end_idx,
                raw_text=section_text
            )
        )

    return sections
