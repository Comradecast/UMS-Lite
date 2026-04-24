"""
Senate eFD Source Downloader.
"""
from typing import List
from pathlib import Path
from transparencyx.sources import SourceDownloader

class SenateDownloader(SourceDownloader):
    @property
    def chamber_name(self) -> str:
        return "senate"

    def download(self, year: int) -> List[Path]:
        """
        Simulates downloading the Senate disclosure reports for the specified year.
        Returns the expected file path.
        """
        download_dir = self.get_download_path(year)
        download_dir.mkdir(parents=True, exist_ok=True)

        # In the future, this will interface with the Senate public disclosure search
        expected_file = download_dir / f"senate_reports_{year}.csv"

        # Return what *would* have been downloaded
        return [expected_file]
