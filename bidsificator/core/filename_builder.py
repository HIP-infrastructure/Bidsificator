"""
BIDS Filename Builder

Schema-driven filename construction with validation against BIDS specification.
Centralizes all filename building logic to ensure consistency and compliance.
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .schema import BidsSchemaManager
from .bids_constants import get_entity_order, get_default_suffix_for_datatype


class FilenameBuilder:
    """Schema-driven BIDS filename builder with validation"""

    def __init__(self):
        self.schema = BidsSchemaManager.get_instance()
        self._entity_order = get_entity_order()

    def build_filename(
        self,
        entities: Dict[str, str],
        suffix: str,
        extension: str,
        validate: bool = True
    ) -> str:
        """
        Build a BIDS-compliant filename from entities.

        Args:
            entities: Dictionary of entity key-value pairs (e.g., {'sub': 'P001', 'ses': 'pre'})
            suffix: File suffix (e.g., 'T1w', 'ieeg', 'bold')
            extension: File extension (e.g., '.nii.gz', '.edf', '.json')
            validate: Whether to validate entities against schema (default: True)

        Returns:
            BIDS-compliant filename (e.g., 'sub-P001_ses-pre_T1w.nii.gz')

        Raises:
            ValueError: If validation fails
        """
        if validate:
            self._validate_entities(entities)

        # Build filename parts in canonical order
        filename_parts = []

        for entity_key in self._entity_order:
            if entity_key in entities:
                value = entities[entity_key]
                # Skip empty or whitespace-only values
                if value and str(value).strip():
                    filename_parts.append(self._format_entity(entity_key, value))

        # Add any entities not in standard order (should be rare with proper schema)
        remaining_entities = set(entities.keys()) - set(self._entity_order)
        for entity_key in sorted(remaining_entities):
            value = entities[entity_key]
            if value and str(value).strip():
                filename_parts.append(self._format_entity(entity_key, value))

        # Build final filename
        filename = "_".join(filename_parts)

        # Add suffix if provided
        if suffix:
            filename = f"{filename}_{suffix}"

        # Add extension
        if not extension.startswith('.'):
            extension = f".{extension}"
        filename = f"{filename}{extension}"

        return filename

    def build_path(
        self,
        dataset_root: Path,
        entities: Dict[str, str],
        datatype: str,
        suffix: str,
        extension: str,
        validate: bool = True
    ) -> Path:
        """
        Build complete BIDS-compliant file path.

        Args:
            dataset_root: Root directory of BIDS dataset
            entities: Entity key-value pairs (must include 'sub')
            datatype: BIDS datatype (e.g., 'ieeg', 'anat', 'func')
            suffix: File suffix
            extension: File extension
            validate: Whether to validate against schema

        Returns:
            Complete Path object

        Raises:
            ValueError: If 'sub' entity is missing or validation fails
        """
        if 'sub' not in entities:
            raise ValueError("'sub' entity is required for BIDS paths")

        if validate:
            self._validate_datatype(datatype)
            self._validate_suffix(datatype, suffix)

        # Build directory structure
        path_parts = [dataset_root]

        # Subject directory: sub-<label>
        path_parts.append(f"sub-{entities['sub']}")

        # Session directory (optional): ses-<label>
        if 'ses' in entities and entities['ses']:
            path_parts.append(f"ses-{entities['ses']}")

        # Datatype directory
        path_parts.append(datatype)

        # Build filename
        filename = self.build_filename(entities, suffix, extension, validate=validate)
        path_parts.append(filename)

        return Path(*path_parts)

    def parse_filename(self, filename: str) -> Tuple[Dict[str, str], str, str]:
        """
        Parse a BIDS filename into entities, suffix, and extension.

        Args:
            filename: BIDS filename to parse

        Returns:
            Tuple of (entities dict, suffix, extension)

        Example:
            >>> parse_filename('sub-P001_ses-pre_task-rest_run-1_ieeg.edf')
            ({'sub': 'P001', 'ses': 'pre', 'task': 'rest', 'run': '1'}, 'ieeg', '.edf')
        """
        # Extract extension
        path = Path(filename)

        # Handle double extensions like .nii.gz
        if path.suffix in ['.gz', '.bz2'] and path.stem.endswith('.nii'):
            extension = '.nii' + path.suffix
            stem = path.stem[:-4]  # Remove .nii
        else:
            extension = path.suffix
            stem = path.stem

        # Split by underscore
        parts = stem.split('_')

        entities = {}
        suffix = None

        for part in parts:
            if '-' in part:
                # Entity: key-value
                key, value = part.split('-', 1)
                entities[key] = value
            else:
                # Last part without dash is the suffix
                suffix = part

        return entities, suffix, extension

    def _format_entity(self, entity_key: str, entity_value: str) -> str:
        """Format entity as key-value pair (e.g., 'sub-P001')"""
        # Remove any existing prefix
        value = str(entity_value)
        if value.startswith(f"{entity_key}-"):
            value = value[len(entity_key)+1:]

        return f"{entity_key}-{value}"

    def _validate_entities(self, entities: Dict[str, str]):
        """Validate entity keys against schema"""
        # Get all valid entity keys from schema
        valid_entities = set(self._entity_order)

        # Check for invalid entities
        invalid = set(entities.keys()) - valid_entities
        if invalid:
            raise ValueError(
                f"Invalid BIDS entities: {invalid}. "
                f"Valid entities: {sorted(valid_entities)}"
            )

    def _validate_datatype(self, datatype: str):
        """Validate datatype against schema"""
        if datatype not in self.schema.datatypes:
            valid_datatypes = sorted(self.schema.datatypes.keys())
            raise ValueError(
                f"Invalid datatype '{datatype}'. "
                f"Valid datatypes: {valid_datatypes}"
            )

    def _validate_suffix(self, datatype: str, suffix: str):
        """Validate suffix for given datatype"""
        if datatype not in self.schema.datatypes:
            return  # Skip if datatype is invalid (will be caught elsewhere)

        dt = self.schema.get_datatype(datatype)
        if suffix not in dt.suffixes:
            raise ValueError(
                f"Invalid suffix '{suffix}' for datatype '{datatype}'. "
                f"Valid suffixes: {sorted(dt.suffixes)[:10]}..."
            )

    def get_default_suffix(self, datatype: str) -> str:
        """Get default suffix for a datatype"""
        return get_default_suffix_for_datatype(datatype)

    def suggest_entities_for_datatype(self, datatype: str) -> List[str]:
        """
        Suggest commonly used entities for a given datatype.

        Args:
            datatype: BIDS datatype

        Returns:
            List of entity keys commonly used with this datatype
        """
        # Common entities for all datatypes
        common = ['sub', 'ses']

        # Datatype-specific entities
        specific = {
            'ieeg': ['task', 'acq', 'run'],
            'eeg': ['task', 'acq', 'run'],
            'meg': ['task', 'acq', 'run', 'proc'],
            'anat': ['acq', 'ce', 'rec', 'run'],
            'func': ['task', 'acq', 'ce', 'dir', 'rec', 'run', 'echo'],
            'dwi': ['acq', 'dir', 'run'],
            'fmap': ['acq', 'ce', 'dir', 'run'],
            'perf': ['acq', 'rec', 'run'],
            'pet': ['acq', 'rec', 'run'],
        }

        return common + specific.get(datatype, [])