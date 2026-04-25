"""
Senate eFD Source.
"""
from typing import List
from pathlib import Path
from transparencyx.sources.base import DisclosureSource

class SenateSource(DisclosureSource):
    @property
    def chamber_name(self) -> str:
        return "senate"

    def fetch(self, year: int) -> List[Path]:
        """
        Simulates downloading the Senate disclosure reports for the specified year.
        Creates a placeholder file and returns the path.
        """
        download_dir = self.get_download_path(year)
        download_dir.mkdir(parents=True, exist_ok=True)

        expected_file = download_dir / f"senate_reports_{year}.csv"
        expected_file.touch()

        return [expected_file]
