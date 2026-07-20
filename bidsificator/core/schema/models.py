"""
BIDS Schema data models

Defines the core data structures for BIDS entities and datatypes.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class EntityFormat(Enum):
    """Format types for BIDS entities"""
    LABEL = "label"
    INDEX = "index"
    ALPHANUMERIC = "alphanumeric"


@dataclass
class BidsEntity:
    """Represents a BIDS entity (sub-, ses-, task-, etc.)"""
    name: str
    key: str  # "sub", "ses", "task", etc.
    required: bool
    format: EntityFormat
    pattern: str  # regex pattern
    description: str

    def validate(self, value: str) -> bool:
        """Validate entity value against pattern"""
        if self.format == EntityFormat.INDEX:
            try:
                int(value)
                return True
            except ValueError:
                return False
        return bool(re.fullmatch(self.pattern, value))

    def format_value(self, value: str) -> str:
        """Format value with entity prefix"""
        return f"{self.key}-{value}"


@dataclass
class BidsDatatype:
    """Represents a BIDS datatype/modality"""
    name: str  # "ieeg", "anat", "func", etc.
    allowed_entities: list[str]
    required_entities: list[str]
    suffixes: list[str]  # "T1w", "T2w", "channels", "events"
    extensions: list[str]  # Extensions from registry
    metadata_requirements: dict[str, Any]

    def build_path(self, entities: dict[str, str], suffix: str, extension: str) -> str:
        """Build BIDS-compliant path using FilenameBuilder"""
        # Import here to avoid circular imports
        from pathlib import Path

        from ..filename_builder import FilenameBuilder

        # Validate required entities
        for req in self.required_entities:
            if req not in entities:
                raise ValueError(f"Required entity '{req}' missing for {self.name}")

        # Use FilenameBuilder for consistent path construction
        builder = FilenameBuilder()

        # Build path from root (empty Path)
        full_path = builder.build_path(
            dataset_root=Path(),
            entities=entities,
            datatype=self.name,
            suffix=suffix,
            extension=extension,
            validate=False  # Skip validation for internal use
        )

        # Return as string with forward slashes
        return str(full_path).replace('\\', '/')

    def get_required_metadata(self, suffix: str = None) -> dict[str, Any]:
        """Get required metadata fields"""
        base_metadata = self.metadata_requirements.get("required", {})
        if suffix and f"suffix_{suffix}" in self.metadata_requirements:
            base_metadata.update(self.metadata_requirements[f"suffix_{suffix}"])
        return base_metadata

    def get_recommended_metadata(self, suffix: str = None) -> dict[str, Any]:
        """Get recommended metadata fields"""
        base_metadata = self.metadata_requirements.get("recommended", {})
        if suffix and f"suffix_{suffix}_recommended" in self.metadata_requirements:
            base_metadata.update(self.metadata_requirements[f"suffix_{suffix}_recommended"])
        return base_metadata

    def get_all_metadata(self, suffix: str = None) -> dict[str, dict[str, Any]]:
        """Get both required and recommended metadata fields"""
        return {
            "required": self.get_required_metadata(suffix),
            "recommended": self.get_recommended_metadata(suffix)
        }
