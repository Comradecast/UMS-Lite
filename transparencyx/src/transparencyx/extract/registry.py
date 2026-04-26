"""
Extractor registry for finding appropriate extractors based on file types.
"""
from typing import Optional
from transparencyx.extract.base import Extractor
from transparencyx.extract.pdf import PDFExtractor
from transparencyx.sources.base import DisclosureSource


def get_extractor_for_source(source: DisclosureSource, file_type: str) -> Optional[Extractor]:
    """
    Returns an appropriate Extractor instance based on the source and file extension.
    If no extractor supports the file type, returns None.

    file_type should be the extension without the dot (e.g., 'pdf', 'csv')
    """
    extractors = [
        PDFExtractor()
        # Other extractors (e.g., CSV, XML) will be registered here in future phases
    ]

    for extractor in extractors:
        if extractor.supports_file_type(file_type):
            return extractor

    return None
