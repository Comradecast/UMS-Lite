"""
Abstract base classes for data sources.
"""
from abc import ABC, abstractmethod
from typing import List
from pathlib import Path

from transparencyx.config import get_raw_data_dir

class DisclosureSource(ABC):
    """
    Abstract base class for a congressional data source.
    """

    @property
    @abstractmethod
    def chamber_name(self) -> str:
        """Returns the name of the chamber (e.g., 'house', 'senate')."""
        pass

    def get_download_path(self, year: int) -> Path:
        """Returns the base directory where downloads for a given year are stored."""
        return get_raw_data_dir(self.chamber_name, year)

    @abstractmethod
    def fetch(self, year: int) -> List[Path]:
        """
        Simulates the download/fetch of disclosure files for the given year.
        Currently offline; returns deterministic file paths and creates placeholder files.
        """
        pass
