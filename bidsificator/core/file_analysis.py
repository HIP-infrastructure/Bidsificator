"""
File analysis utilities for BIDS processing
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bidsificator.converters.base import FormatConverter


@dataclass
class FileAnalysis:
    """Result of analyzing a file for BIDS processing"""
    source_path: Path
    needs_conversion: bool
    converter: FormatConverter | None
    bids_datatype: str | None
    error: str | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_valid(self) -> bool:
        """Check if file can be processed"""
        return self.error is None

    @property
    def converter_name(self) -> str | None:
        """Get converter class name if available"""
        return self.converter.__class__.__name__ if self.converter else None
