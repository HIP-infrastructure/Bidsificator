"""
BIDS Schema data models

Defines the core data structures for BIDS entities and datatypes.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum
import re

from ..bids_constants import ENTITY_ORDER


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
    allowed_entities: List[str]
    required_entities: List[str]
    suffixes: List[str]  # "T1w", "T2w", "channels", "events"
    extensions: List[str]  # Extensions from registry
    metadata_requirements: Dict[str, Any]
    
    def build_path(self, entities: Dict[str, str], suffix: str, extension: str) -> str:
        """Build BIDS-compliant path"""
        # Validate required entities
        for req in self.required_entities:
            if req not in entities:
                raise ValueError(f"Required entity '{req}' missing for {self.name}")
        
        # Build path components
        path_parts = []
        
        # Subject directory
        if "sub" in entities:
            path_parts.append(f"sub-{entities['sub']}")
        
        # Session directory (optional)
        if "ses" in entities:
            path_parts.append(f"ses-{entities['ses']}")
        
        # Datatype directory
        path_parts.append(self.name)
        
        # Build filename
        filename_parts = []
        
        # Add entities in BIDS order
        for entity_key in ENTITY_ORDER:
            if entity_key in entities:
                filename_parts.append(f"{entity_key}-{entities[entity_key]}")
        
        # Add suffix and extension
        filename = "_".join(filename_parts)
        if suffix:
            filename = f"{filename}_{suffix}"
        filename = f"{filename}{extension}"
        
        path_parts.append(filename)
        return "/".join(path_parts)
    
    def get_required_metadata(self, suffix: str = None) -> Dict[str, Any]:
        """Get required metadata fields"""
        base_metadata = self.metadata_requirements.get("required", {})
        if suffix and f"suffix_{suffix}" in self.metadata_requirements:
            base_metadata.update(self.metadata_requirements[f"suffix_{suffix}"])
        return base_metadata
    
    def get_recommended_metadata(self, suffix: str = None) -> Dict[str, Any]:
        """Get recommended metadata fields"""
        base_metadata = self.metadata_requirements.get("recommended", {})
        if suffix and f"suffix_{suffix}_recommended" in self.metadata_requirements:
            base_metadata.update(self.metadata_requirements[f"suffix_{suffix}_recommended"])
        return base_metadata
    
    def get_all_metadata(self, suffix: str = None) -> Dict[str, Dict[str, Any]]:
        """Get both required and recommended metadata fields"""
        return {
            "required": self.get_required_metadata(suffix),
            "recommended": self.get_recommended_metadata(suffix)
        }