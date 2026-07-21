"""
Base classes for format converters
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class FormatConverter(ABC):
    """Base class for all format converters"""

    @property
    @abstractmethod
    def source_extensions(self) -> list[str]:
        """File extensions this converter handles"""
        pass

    @property
    @abstractmethod
    def target_format(self) -> str:
        """BIDS-compliant format this converter produces"""
        pass

    @abstractmethod
    def convert(self, source_path: Path, output_dir: Path = None) -> Path:
        """
        Convert file to BIDS-compliant format
        Returns path to converted file
        """
        pass

    @abstractmethod
    def can_convert(self, source_path: Path) -> bool:
        """Check if this converter can handle the file"""
        pass

    def extract_metadata(self, source_path: Path) -> dict[str, Any]:
        """Extract metadata from source file for BIDS JSON sidecar"""
        return {}

    @property
    def priority(self) -> int:
        """Priority for this converter (higher = preferred). Default: 0"""
        return 0

    @property
    def description(self) -> str:
        """Human-readable description of this converter"""
        return f"Convert {', '.join(self.source_extensions)} to {self.target_format}"
