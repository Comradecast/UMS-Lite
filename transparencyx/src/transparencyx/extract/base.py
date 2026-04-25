"""
Base definitions for the extraction layer.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from transparencyx.sources.base import DisclosureSource


@dataclass
class ExtractionResult:
    """
    Structured result of an extraction operation.
    """
    source: DisclosureSource
    file_path: Path
    success: bool
    extracted_text: Optional[str] = None
    error: Optional[str] = None


class Extractor(ABC):
    """
    Abstract base class for document extractors.
    """

    @abstractmethod
    def supports_file_type(self, file_type: str) -> bool:
        """
        Check if the extractor supports the given file extension (e.g., 'pdf', 'csv', 'zip').
        """
        pass

    @abstractmethod
    def extract(self, file_path: Path, source: DisclosureSource) -> ExtractionResult:
        """
        Extract text from the given file.
        """
        pass
