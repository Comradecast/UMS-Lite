from pathlib import Path
from transparencyx.config import get_raw_data_dir
from transparencyx.sources.house import HouseDownloader
from transparencyx.sources.senate import SenateDownloader

def test_get_raw_data_dir():
    path = get_raw_data_dir("house", 2023)
    assert path.name == "2023"
    assert path.parent.name == "house"
    assert path.parent.parent.name == "raw"

def test_house_downloader_offline():
    downloader = HouseDownloader()
    assert downloader.chamber_name == "house"

    paths = downloader.download(2023)
    assert len(paths) == 1
    assert paths[0].name == "2023FD.zip"
    assert paths[0].parent.name == "2023"

def test_senate_downloader_offline():
    downloader = SenateDownloader()
    assert downloader.chamber_name == "senate"

    paths = downloader.download(2024)
    assert len(paths) == 1
    assert paths[0].name == "senate_reports_2024.csv"
    assert paths[0].parent.name == "2024"
