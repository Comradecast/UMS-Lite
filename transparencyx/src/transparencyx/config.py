import os
from pathlib import Path

# Base directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"

def get_raw_data_dir(chamber: str, year: int) -> Path:
    """
    Returns the deterministic raw data directory for a specific chamber and year.
    Creates the directory if it does not exist.
    """
    path = RAW_DATA_DIR / chamber.lower() / str(year)
    return path
