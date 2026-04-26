"""
House Clerk Financial Disclosure Source.
"""
from typing import List
from pathlib import Path
from transparencyx.sources.base import DisclosureSource

class HouseSource(DisclosureSource):
    @property
    def chamber_name(self) -> str:
        return "house"

    def fetch(self, year: int) -> List[Path]:
        """
        Simulates downloading the House disclosure index for the specified year.
        Creates a placeholder file and returns the path.
        """
        download_dir = self.get_download_path(year)
        download_dir.mkdir(parents=True, exist_ok=True)

        expected_file = download_dir / f"{year}FD.zip"
        expected_file.touch()

        return [expected_file]
