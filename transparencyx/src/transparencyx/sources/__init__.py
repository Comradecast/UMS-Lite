"""
Source modules for TransparencyX. Contains interfaces and downloader logic for
official House and Senate disclosures.
"""
from abc import ABC, abstractmethod
from typing import List
from pathlib import Path

from transparencyx.config import get_raw_data_dir

class SourceDownloader(ABC):
    """
    Abstract base class for chamber-specific source downloaders.
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
    def download(self, year: int) -> List[Path]:
        """
        Simulates the download of disclosure files for the given year.
        Currently offline; returns deterministic file paths that would be created.
        """
        pass
