import sys
from pathlib import Path
from unittest.mock import patch
import pytest

from transparencyx.sources.registry import get_registered_sources
from transparencyx.sources.downloader import Downloader
from transparencyx.cli import main

def test_registry_returns_sources():
    sources = get_registered_sources()
    assert "house" in sources
    assert "senate" in sources
    assert sources["house"].chamber_name == "house"
    assert sources["senate"].chamber_name == "senate"

def test_sources_list_command(capsys):
    test_args = ["transparencyx", "sources", "list"]
    with patch.object(sys, 'argv', test_args):
        main()
    captured = capsys.readouterr()
    assert "house" in captured.out
    assert "senate" in captured.out

def test_fetch_all_creates_placeholders(tmp_path, monkeypatch):
    # Monkeypatch RAW_DATA_DIR to point to tmp_path so we don't dirty the workspace
    import transparencyx.config as config
    monkeypatch.setattr(config, "RAW_DATA_DIR", tmp_path / "raw")

    downloader = Downloader()
    paths = downloader.fetch_all(2023)

    assert len(paths) == 2
    for path in paths:
        assert path.exists()
        assert path.is_file()
        assert "2023" in str(path)

def test_fetch_chamber_house_creates_placeholders(tmp_path, monkeypatch):
    import transparencyx.config as config
    monkeypatch.setattr(config, "RAW_DATA_DIR", tmp_path / "raw")

    downloader = Downloader()
    paths = downloader.fetch_chamber("house", 2023)

    assert len(paths) == 1
    assert paths[0].exists()
    assert paths[0].name == "2023FD.zip"

    # Verify senate path was NOT created
    senate_dir = tmp_path / "raw" / "senate" / "2023"
    assert not senate_dir.exists()
