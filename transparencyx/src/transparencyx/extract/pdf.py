"""
PDF extraction logic using pypdf.
"""
from pathlib import Path
import pypdf

from transparencyx.extract.base import Extractor, ExtractionResult
from transparencyx.sources.base import DisclosureSource


class PDFExtractor(Extractor):
    """
    Extractor for PDF financial disclosures.
    Extracts raw text only, no parsing or regex.
    """
    def supports_file_type(self, file_type: str) -> bool:
        return file_type.lower() == "pdf"

    def extract(self, file_path: Path, source: DisclosureSource) -> ExtractionResult:
        """
        Opens the PDF and extracts raw text across all pages.
        """
        extracted_text = ""

        try:
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)

                # Check for empty PDF (0 pages)
                if len(reader.pages) == 0:
                    return ExtractionResult(
                        source=source,
                        file_path=file_path,
                        success=False,
                        extracted_text=None,
                        error="PDF has 0 pages"
                    )

                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"

            if not extracted_text.strip():
                 return ExtractionResult(
                    source=source,
                    file_path=file_path,
                    success=False,
                    extracted_text=None,
                    error="No readable text found in PDF"
                )

            return ExtractionResult(
                source=source,
                file_path=file_path,
                success=True,
                extracted_text=extracted_text.strip(),
                error=None
            )

        except Exception as e:
            return ExtractionResult(
                source=source,
                file_path=file_path,
                success=False,
                extracted_text=None,
                error=str(e)
            )
