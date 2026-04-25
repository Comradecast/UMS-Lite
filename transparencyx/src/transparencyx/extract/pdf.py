"""
PDF extraction stub.
"""
from pathlib import Path
from transparencyx.extract.base import Extractor, ExtractionResult
from transparencyx.sources.base import DisclosureSource


class PDFExtractor(Extractor):
    """
    Stub extractor for PDF financial disclosures.
    """
    def supports_file_type(self, file_type: str) -> bool:
        return file_type.lower() == "pdf"

    def extract(self, file_path: Path, source: DisclosureSource) -> ExtractionResult:
        """
        Returns a placeholder extraction result without actually parsing the PDF.
        """
        return ExtractionResult(
            source=source,
            file_path=file_path,
            success=True,
            extracted_text="PDF extraction not implemented",
            error=None
        )
