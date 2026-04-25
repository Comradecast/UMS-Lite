import sys
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from transparencyx.extract.registry import get_extractor_for_source
from transparencyx.extract.pdf import PDFExtractor
from transparencyx.cli import main

def test_registry_returns_pdf_extractor():
    extractor = get_extractor_for_source("pdf")
    assert isinstance(extractor, PDFExtractor)

def test_registry_returns_none_for_unknown():
    extractor = get_extractor_for_source("unknown_ext")
    assert extractor is None

def test_pdf_extractor_stub():
    extractor = PDFExtractor()
    assert extractor.supports_file_type("pdf") is True
    assert extractor.supports_file_type("csv") is False

    file_path = Path("/fake/path.pdf")
    result = extractor.extract(file_path, "house")

    assert result.source == "house"
    assert result.file_path == file_path
    assert result.success is True
    assert result.extracted_text == "PDF extraction not implemented"
    assert result.error is None

def test_extract_cli_command(tmp_path, monkeypatch, capsys):
    # Setup mock data directory
    import transparencyx.cli as cli
    monkeypatch.setattr(cli, "RAW_DATA_DIR", tmp_path / "raw")

    # Create test files
    house_dir = tmp_path / "raw" / "house" / "2023"
    house_dir.mkdir(parents=True)
    (house_dir / "report1.pdf").touch()
    (house_dir / "data.zip").touch()

    senate_dir = tmp_path / "raw" / "senate" / "2023"
    senate_dir.mkdir(parents=True)
    (senate_dir / "report2.pdf").touch()

    # Run CLI command
    test_args = ["transparencyx", "extract", "--all"]
    with patch.object(sys, 'argv', test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    # We expect 3 results
    assert len(output) == 3

    pdf_results = [r for r in output if r["file_path"].endswith(".pdf")]
    zip_results = [r for r in output if r["file_path"].endswith(".zip")]

    assert len(pdf_results) == 2
    for r in pdf_results:
        assert r["success"] is True
        assert r["extracted_text"] == "PDF extraction not implemented"

    assert len(zip_results) == 1
    assert zip_results[0]["success"] is False
    assert "No extractor found" in zip_results[0]["error"]
