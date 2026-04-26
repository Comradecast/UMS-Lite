import re
from transparencyx.models import DisclosureRange

def parse_range(label: str) -> DisclosureRange:
    """
    Parses a common disclosure range label.
    It does not guess values. If parsing fails, it returns None for min, max, and mid.
    """
    label_clean = label.strip()

    # Handle explicit none/N/A
    lower_label = label_clean.lower()
    if lower_label == "none":
        return DisclosureRange(
            original_label=label,
            minimum=0,
            maximum=0,
            midpoint=0
        )

    if lower_label in ("n/a", ""):
        return DisclosureRange(
            original_label=label,
            minimum=None,
            maximum=None,
            midpoint=None
        )

    # Handle "Over X" format
    over_match = re.match(r"(?i)^over\s*\$([\d,]+)$", label_clean)
    if over_match:
        min_val_str = over_match.group(1).replace(",", "")
        try:
            min_val = int(min_val_str)
            return DisclosureRange(
                original_label=label,
                minimum=min_val,
                maximum=None,
                midpoint=None
            )
        except ValueError:
            pass

    # Handle standard ranges like "$1,001 - $15,000"
    range_match = re.match(r"^\$([\d,]+)\s*-\s*\$([\d,]+)$", label_clean)
    if range_match:
        min_val_str = range_match.group(1).replace(",", "")
        max_val_str = range_match.group(2).replace(",", "")
        try:
            min_val = int(min_val_str)
            max_val = int(max_val_str)
            mid_val = (min_val + max_val) // 2
            return DisclosureRange(
                original_label=label,
                minimum=min_val,
                maximum=max_val,
                midpoint=mid_val
            )
        except ValueError:
            pass

    # Default fallback for unparseable ranges
    return DisclosureRange(
        original_label=label,
        minimum=None,
        maximum=None,
        midpoint=None
    )
