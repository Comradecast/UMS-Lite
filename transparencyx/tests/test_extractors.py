import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import pypdf

from transparencyx.sources.house import HouseSource
from transparencyx.extract.registry import get_extractor_for_source
from transparencyx.extract.pdf import PDFExtractor
from transparencyx.cli import main

def test_registry_returns_pdf_extractor():
    source = HouseSource()
    extractor = get_extractor_for_source(source, "pdf")
    assert isinstance(extractor, PDFExtractor)

def test_registry_returns_none_for_unknown():
    source = HouseSource()
    extractor = get_extractor_for_source(source, "unknown_ext")
    assert extractor is None

def test_pdf_extractor_valid_pdf_no_text(tmp_path):
    extractor = PDFExtractor()
    assert extractor.supports_file_type("pdf") is True
    assert extractor.supports_file_type("csv") is False

    # Create a valid minimal PDF using pypdf writer
    pdf_path = tmp_path / "valid.pdf"
    writer = pypdf.PdfWriter()
    # Add a blank page to make it structurally valid,
    # though it will have no text, we can check the error "No readable text"
    writer.add_blank_page(width=200, height=200)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    source = HouseSource()
    result = extractor.extract(pdf_path, source)

    assert result.source == source
    assert result.file_path == pdf_path
    assert result.success is False
    assert result.extracted_text is None
    assert result.error == "No readable text found in PDF"

@patch("transparencyx.extract.pdf.pypdf.PdfReader")
def test_pdf_extractor_success(mock_pdf_reader, tmp_path):
    extractor = PDFExtractor()

    # Setup mock to simulate a PDF with text
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Mocked PDF text"

    mock_reader_instance = mock_pdf_reader.return_value
    mock_reader_instance.pages = [mock_page]

    pdf_path = tmp_path / "mocked.pdf"
    pdf_path.touch()

    source = HouseSource()
    result = extractor.extract(pdf_path, source)

    assert result.success is True
    assert result.extracted_text == "Mocked PDF text"
    assert result.error is None

def test_pdf_extractor_corrupt_pdf(tmp_path):
    extractor = PDFExtractor()

    # Create a fake/corrupt PDF
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_text("This is not a real PDF file")

    source = HouseSource()
    result = extractor.extract(pdf_path, source)

    assert result.source == source
    assert result.file_path == pdf_path
    assert result.success is False
    assert result.extracted_text is None
    assert result.error is not None
    assert "Stream has ended unexpectedly" in result.error or "EOF marker not found" in result.error or "PdfReadError" in result.error

def test_extract_cli_command(tmp_path, monkeypatch, capsys):
    # Setup mock data directory
    import transparencyx.cli as cli
    monkeypatch.setattr(cli, "RAW_DATA_DIR", tmp_path / "raw")

    # Create test files
    house_dir = tmp_path / "raw" / "house" / "2023"
    house_dir.mkdir(parents=True)

    # We create invalid PDFs, so they will be correctly identified as failures
    (house_dir / "report1.pdf").write_text("fake pdf")
    (house_dir / "data.zip").touch()

    senate_dir = tmp_path / "raw" / "senate" / "2023"
    senate_dir.mkdir(parents=True)
    (senate_dir / "report2.pdf").write_text("fake pdf")

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
        # Since we gave it fake PDFs, it should fail parsing
        assert r["success"] is False
        assert "error" in r
        assert "Stream has ended unexpectedly" in r["error"] or "EOF marker not found" in r["error"] or "PdfReadError" in r["error"]

    assert len(zip_results) == 1
    assert zip_results[0]["success"] is False
    assert "No extractor found" in zip_results[0]["error"]
