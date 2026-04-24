"""
House Clerk Financial Disclosure Source Downloader.
"""
from typing import List
from pathlib import Path
from transparencyx.sources import SourceDownloader

class HouseDownloader(SourceDownloader):
    @property
    def chamber_name(self) -> str:
        return "house"

    def download(self, year: int) -> List[Path]:
        """
        Simulates downloading the House disclosure index for the specified year.
        Returns the expected file path.
        """
        download_dir = self.get_download_path(year)
        download_dir.mkdir(parents=True, exist_ok=True)

        # In the future, this will fetch the zip/xml from the House Clerk
        expected_file = download_dir / f"{year}FD.zip"

        # Return what *would* have been downloaded
        return [expected_file]
