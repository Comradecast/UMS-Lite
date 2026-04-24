"""
Downloader orchestration.
"""
from typing import List, Optional
from pathlib import Path
from transparencyx.sources.registry import get_registered_sources

class Downloader:
    """
    Orchestrates fetching data across registered sources.
    """
    def __init__(self):
        self.sources = get_registered_sources()

    def fetch_all(self, year: int) -> List[Path]:
        """Fetches data from all registered sources for the given year."""
        paths = []
        for source in self.sources.values():
            paths.extend(source.fetch(year))
        return paths

    def fetch_chamber(self, chamber: str, year: int) -> List[Path]:
        """Fetches data for a specific chamber and year."""
        source = self.sources.get(chamber.lower())
        if not source:
            raise ValueError(f"Unknown chamber: {chamber}")
        return source.fetch(year)
