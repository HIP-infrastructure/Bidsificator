"""
BIDS Schema Manager

Manages the embedded BIDS schema and provides access to parsed schema components.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from .models import BidsEntity, BidsDatatype
from .parser import BidsSchemaParser
from .file_extensions import FileExtensionRegistry

logger = logging.getLogger(__name__)


class BidsSchemaManager:
    """Manages the embedded BIDS schema (Singleton)"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, schema_path: Path = None):
        if cls._instance is None:
            cls._instance = super(BidsSchemaManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, schema_path: Path = None):
        # Only initialize once
        if BidsSchemaManager._initialized:
            return
            
        if schema_path is None:
            # Default to embedded schema
            schema_path = Path(__file__).parent.parent.parent / "schema" / "bids_schema.json"
        
        self.schema_path = schema_path
        self._raw_schema = None
        self.entities: Dict[str, BidsEntity] = {}
        self.datatypes: Dict[str, BidsDatatype] = {}
        self.metadata_fields: Dict[str, Any] = {}
        self.filename_templates: Dict[str, str] = {}
        self.file_registry: Optional[FileExtensionRegistry] = None
        self._parser = BidsSchemaParser()
        
        BidsSchemaManager._initialized = True
        
    @classmethod 
    def get_instance(cls) -> 'BidsSchemaManager':
        """Get the singleton instance, loading schema if needed"""
        if cls._instance is None:
            cls._instance = cls()
        cls._instance.load_schema()
        return cls._instance
        
    def load_schema(self) -> None:
        """Load and parse the BIDS schema (only once)"""
        # If schema is already loaded, don't reload
        if self._raw_schema is not None:
            return
            
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                self._raw_schema = json.load(f)
            
            self._parse_schema()
            
            # Initialize file extension registry
            self.file_registry = FileExtensionRegistry(self)
            
            logger.info("Loaded BIDS schema version %s", self.get_bids_version())
            
        except FileNotFoundError:
            raise FileNotFoundError(f"BIDS schema file not found: {self.schema_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file: {e}")
    
    def _parse_schema(self) -> None:
        """Parse schema into usable components"""
        if not self._raw_schema:
            raise RuntimeError("Schema not loaded. Call load_schema() first.")
        
        self.entities = self._parser.parse_entities(self._raw_schema)
        self.datatypes = self._parser.parse_datatypes(self._raw_schema)
        self.metadata_fields = self._parser.parse_metadata(self._raw_schema)
        self.filename_templates = self._parser.build_filename_templates(self._raw_schema)
    
    def get_datatype(self, name: str) -> Optional[BidsDatatype]:
        """Get datatype definition by name"""
        return self.datatypes.get(name)
    
    def get_entity(self, name: str) -> Optional[BidsEntity]:
        """Get entity definition by name"""
        return self.entities.get(name)
    
    def get_datatypes(self) -> List[str]:
        """Get list of available datatypes"""
        return list(self.datatypes.keys())
    
    def get_entities(self) -> List[str]:
        """Get list of available entities"""
        return list(self.entities.keys())
    
    def validate_entity_value(self, entity_name: str, value: str) -> bool:
        """Validate an entity value against schema"""
        entity = self.get_entity(entity_name)
        if not entity:
            return False
        return entity.validate(value)
    
    def get_required_metadata(self, datatype: str, suffix: str = None) -> Dict[str, Any]:
        """Get required metadata fields for datatype/suffix"""
        dt = self.get_datatype(datatype)
        if not dt:
            return {}
        return dt.get_required_metadata(suffix)
    
    def get_allowed_entities(self, datatype: str) -> List[str]:
        """Get allowed entities for a datatype"""
        dt = self.get_datatype(datatype)
        if not dt:
            return []
        return dt.allowed_entities
    
    def get_required_entities(self, datatype: str) -> List[str]:
        """Get required entities for a datatype"""
        dt = self.get_datatype(datatype)
        if not dt:
            return ["sub"]  # Subject always required
        return dt.required_entities
    
    def get_suffixes(self, datatype: str) -> List[str]:
        """Get valid suffixes for a datatype"""
        dt = self.get_datatype(datatype)
        if not dt:
            return []
        return dt.suffixes
    
    def build_bids_path(self, datatype: str, entities: Dict[str, str], suffix: str, extension: str) -> str:
        """Build BIDS-compliant path"""
        dt = self.get_datatype(datatype)
        if not dt:
            raise ValueError(f"Unknown datatype: {datatype}")
        
        return dt.build_path(entities, suffix, extension)
    
    def validate_entities_for_datatype(self, datatype: str, entities: Dict[str, str]) -> List[str]:
        """Validate entities for a specific datatype. Returns list of errors."""
        errors = []
        dt = self.get_datatype(datatype)
        
        if not dt:
            errors.append(f"Unknown datatype: {datatype}")
            return errors
        
        # Check required entities
        for req_entity in dt.required_entities:
            if req_entity not in entities:
                errors.append(f"Missing required entity '{req_entity}' for {datatype}")
        
        # Check if entities are allowed
        for entity_key, entity_value in entities.items():
            if entity_key not in dt.allowed_entities:
                errors.append(f"Entity '{entity_key}' not allowed for {datatype}")
            else:
                # Validate entity value format
                entity_def = self.get_entity(entity_key)
                if entity_def and not entity_def.validate(entity_value):
                    errors.append(f"Invalid value for {entity_key}: '{entity_value}'")
        
        return errors
    
    def get_bids_version(self) -> str:
        """Get BIDS specification version"""
        if not self._raw_schema:
            return "unknown"
        return self._raw_schema.get("bids_version", "unknown")
    
    def get_schema_version(self) -> str:
        """Get schema format version"""
        if not self._raw_schema:
            return "unknown"
        return self._raw_schema.get("schema_version", "unknown")
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get comprehensive schema information"""
        if not self._raw_schema:
            return {}
        
        return self._parser.get_schema_info(self._raw_schema)
    
    def is_valid_filename(self, filename: str, datatype: str = None) -> bool:
        """Check if filename follows BIDS naming convention"""
        # Basic check for BIDS filename pattern
        # Should start with sub- and have proper entity format
        if not filename.startswith("sub-"):
            return False
        
        # Extract entities from filename
        entities = self._extract_entities_from_filename(filename)
        
        if not entities:
            return False
        
        if datatype:
            # Validate against specific datatype
            errors = self.validate_entities_for_datatype(datatype, entities)
            return len(errors) == 0
        
        return True
    
    def _extract_entities_from_filename(self, filename: str) -> Dict[str, str]:
        """Extract entities from a BIDS filename"""
        import re

        entities = {}

        # Remove extension and suffix
        name_parts = filename.split('_')

        for part in name_parts[:-1]:  # Skip last part (suffix + extension)
            if '-' in part:
                key, value = part.split('-', 1)
                if key in self.entities:
                    entities[key] = value

        return entities

    def get_entity_order(self) -> List[str]:
        """
        Get canonical entity ordering from BIDS schema.

        Returns entity keys in the order they should appear in BIDS filenames,
        as defined by the BIDS specification.

        Returns:
            List of entity keys in canonical order (e.g., ['sub', 'ses', 'task', ...])
        """
        if not self._raw_schema:
            self.load_schema()
        return self._parser.get_entity_order(self._raw_schema)