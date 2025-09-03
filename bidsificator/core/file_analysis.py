"""
File analysis utilities for BIDS processing
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

from bidsificator.converters.base import FormatConverter


@dataclass
class FileAnalysis:
    """Result of analyzing a file for BIDS processing"""
    source_path: Path
    needs_conversion: bool
    converter: Optional[FormatConverter]
    bids_datatype: Optional[str]
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_valid(self) -> bool:
        """Check if file can be processed"""
        return self.error is None
    
    @property
    def converter_name(self) -> Optional[str]:
        """Get converter class name if available"""
        return self.converter.__class__.__name__ if self.converter else None