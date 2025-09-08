"""
Improved schema-driven BidsSubject implementation

Improvements over BidsSubjectNew:
- No inline classes
- Extracted constants to bids_constants module
- Proper file analysis abstraction
- Cleaner code structure
- Better separation of concerns
"""

import json
import shutil
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile

from bidsificator.core.schema import BidsSchemaManager
from bidsificator.converters.registry import ConverterRegistry
from bidsificator.core.file_analysis import FileAnalysis
from bidsificator.core.bids_constants import (
    DEFAULT_METADATA_VALUES,
    DEFAULT_SUFFIXES,
    ENTITY_ORDER,
    DEFAULT_CHANNEL_COUNTS,
    BIDS_DATA_EXTENSIONS
)


class BidsSubject:
    """Schema-driven BIDS subject with automatic conversion support"""
    
    def __init__(self, subject_id: str, dataset_path: Path, schema_manager: BidsSchemaManager):
        """
        Initialize BIDS subject with schema-driven validation
        
        Args:
            subject_id: Subject identifier (without 'sub-' prefix)
            dataset_path: Path to BIDS dataset root
            schema_manager: Schema manager instance
        """
        self.subject_id = subject_id
        self.dataset_path = Path(dataset_path)
        self.schema = schema_manager
        
        # Sanitize and validate subject ID using schema
        sanitized_subject_id = self._sanitize_subject_id(subject_id)
        if sanitized_subject_id != subject_id:
            print(f"Sanitized subject ID: '{subject_id}' → '{sanitized_subject_id}'")
        
        if not self.schema.validate_entity_value('sub', sanitized_subject_id):
            raise ValueError(f"Invalid subject ID '{sanitized_subject_id}' according to BIDS schema")
        
        # Use sanitized ID
        self.subject_id = sanitized_subject_id
        
        self.subject_path = self._build_subject_path()
        self.subject_path.mkdir(parents=True, exist_ok=True)
        
        # Create default BIDS folder structure (matching old behavior)
        self._create_default_folders()
        
        # Initialize converter registry
        self.converter_registry = ConverterRegistry()
        
        # Track optional metadata for this subject
        self.optional_metadata: Dict[str, Any] = {}
    
    def _sanitize_subject_id(self, subject_id: str) -> str:
        """
        Sanitize subject ID to comply with BIDS specification.
        
        BIDS allows only [a-zA-Z0-9]+ for entity labels.
        This converts common invalid characters to valid ones:
        - Underscores (_) become empty (CHUV_001 → CHUV001)
        - Hyphens (-) become empty (test-123 → test123)
        """
        import re
        # Remove underscores and hyphens - most common violations
        sanitized = re.sub(r'[_-]', '', subject_id)
        
        # Remove any other non-alphanumeric characters
        sanitized = re.sub(r'[^a-zA-Z0-9]', '', sanitized)
        
        # Ensure not empty
        if not sanitized:
            sanitized = 'subject001'
        
        return sanitized
    
    # Backward compatibility methods for existing controllers
    def get_subject_id(self) -> str:
        """Get subject ID (backward compatibility)"""
        return self.subject_id
    
    def get_optional_keys(self) -> dict:
        """Get optional metadata keys (backward compatibility)"""
        return self.optional_metadata
    
    def update_optional_key(self, key: str, value: str = "n/a"):
        """Update optional metadata key (backward compatibility)"""
        self.optional_metadata[key] = value
    
    def add_optional_key(self, key: str, value: str = "n/a"):
        """Add optional metadata key (backward compatibility)"""
        self.optional_metadata[key] = value
    
    def add_optional_key_at(self, position: int, key: str, value: str = "n/a"):
        """Add optional metadata key at specific position (backward compatibility)"""
        # Convert dict to list, insert at position, convert back
        items = list(self.optional_metadata.items())
        items.insert(position, (key, value))
        self.optional_metadata = dict(items)
    
    def remove_optional_key(self, key: str):
        """Remove optional metadata key (backward compatibility)"""
        if key in self.optional_metadata:
            del self.optional_metadata[key]
        else:
            print("Key not found:", key)
    
    def _build_subject_path(self) -> Path:
        """Build subject directory path"""
        return self.dataset_path / self._format_entity('sub', self.subject_id)
    
    def _create_default_folders(self):
        """Create default BIDS folder structure for backward compatibility.
        
        Creates ses-pre and ses-post folders with anat and ieeg subdirectories,
        matching the old BidsSubject behavior.
        """
        # Create session folders with datatype subdirectories
        sessions = ["ses-pre", "ses-post"]
        datatypes = ["anat", "ieeg"]  # Default datatypes for iEEG datasets
        
        for session in sessions:
            for datatype in datatypes:
                folder_path = self.subject_path / session / datatype
                folder_path.mkdir(parents=True, exist_ok=True)
    
    def _format_entity(self, entity_key: str, entity_value: str) -> str:
        """Format entity with prefix (e.g., 'sub-01')"""
        return f"{entity_key}-{entity_value}"
    
    def get_subject_id(self) -> str:
        """Get subject ID without prefix"""
        return self.subject_id
    
    def get_subject_path(self) -> Path:
        """Get full subject directory path"""
        return self.subject_path
    
    def set_optional_metadata(self, metadata: Dict[str, Any]):
        """Set optional metadata that will be included in all files"""
        self.optional_metadata.update(metadata)
    
    def get_datatype_path(self, datatype: str, session: Optional[str] = None) -> Path:
        """
        Get path for a specific datatype, creating directories if needed
        
        Args:
            datatype: BIDS datatype (ieeg, eeg, anat, func, etc.)
            session: Optional session identifier (without 'ses-' prefix)
            
        Returns:
            Path to datatype directory
        """
        # Validate datatype
        if datatype not in self.schema.datatypes:
            available = list(self.schema.datatypes.keys())
            raise ValueError(f"Unknown datatype '{datatype}' - available: {available}")
        
        # Build path
        if session:
            # Validate session ID
            if not self.schema.validate_entity_value('ses', session):
                raise ValueError(f"Invalid session ID '{session}' according to BIDS schema")
            path = self.subject_path / self._format_entity('ses', session) / datatype
        else:
            path = self.subject_path / datatype
        
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def analyze_file(self, source_path: Path, target_format: Optional[str] = None) -> FileAnalysis:
        """
        Analyze file for BIDS processing
        
        Args:
            source_path: Source file path
            target_format: Optional target format for conversion
            
        Returns:
            FileAnalysis object with processing information
        """
        converter = self.converter_registry.get_converter(source_path, target_format)
        
        # Detect datatype from file
        bids_datatype = self._detect_datatype_from_file(source_path)
        
        return FileAnalysis(
            source_path=source_path,
            needs_conversion=converter is not None,
            converter=converter,
            bids_datatype=bids_datatype,
            error=None
        )
    
    def _detect_datatype_from_file(self, file_path: Path) -> str:
        """
        Detect BIDS datatype from file extension
        
        This should ideally use the schema's file registry,
        but provides a simple fallback for common cases
        """
        ext = file_path.suffix.lower()
        
        # Try to use schema's file registry if available
        if hasattr(self.schema, 'file_registry'):
            detected = self.schema.file_registry.detect_datatype(file_path)
            if detected:
                return detected
        
        # Fallback to simple detection
        if ext in ['.trc', '.edf', '.vhdr', '.eeg', '.bdf', '.set']:
            return 'ieeg'  # Default for electrophysiology
        elif ext in ['.nii', '.nii.gz']:
            # Try to detect from filename
            name_lower = file_path.stem.lower()
            if any(x in name_lower for x in ['bold', 'task']):
                return 'func'
            elif 'dwi' in name_lower:
                return 'dwi'
            else:
                return 'anat'  # Default for imaging
        elif ext in ['.fif', '.con', '.raw']:
            return 'meg'
        elif ext == '.snirf':
            return 'nirs'
        
        return 'unknown'
    
    def add_file(self, 
                 source_path: Path,
                 datatype: str,
                 entities: Optional[Dict[str, str]] = None,
                 suffix: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 target_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Add file to subject with automatic conversion and schema-driven naming
        
        Args:
            source_path: Source file path
            datatype: BIDS datatype (ieeg, eeg, anat, etc.)
            entities: BIDS entities dict (sub will be added automatically)
            suffix: BIDS suffix (auto-detected if not provided)
            metadata: Additional metadata for JSON sidecar
            target_format: Force specific conversion target (optional)
            
        Returns:
            Dict with conversion results and target path info
        """
        source_path = Path(source_path)
        entities = entities or {}
        metadata = metadata or {}
        
        # Ensure subject ID is in entities
        entities['sub'] = self.subject_id
        
        # Analyze file
        analysis = self.analyze_file(source_path, target_format)
        
        if analysis.error:
            raise ValueError(f"Cannot process file {source_path.name}: {analysis.error}")
        
        # Handle conversion if needed
        if analysis.needs_conversion:
            final_source, conv_metadata = self._convert_file(
                source_path, 
                analysis.converter
            )
            metadata.update(conv_metadata)
            metadata['SourceFile'] = str(source_path)
            final_datatype = analysis.bids_datatype or datatype
        else:
            final_source = source_path
            final_datatype = datatype or analysis.bids_datatype
        
        # Get datatype definition from schema
        dt = self.schema.get_datatype(final_datatype)
        if not dt:
            raise ValueError(f"Unknown datatype: {final_datatype}")
        
        # Auto-detect suffix if not provided
        if not suffix:
            suffix = self._detect_suffix(final_source, final_datatype)
        
        # Validate entities against schema (suffix-specific validation)
        self._validate_entities_for_suffix(entities, final_datatype, suffix)
        
        # Build BIDS-compliant path
        target_path = self._build_target_path(entities, final_datatype, suffix, final_source.suffix)
        
        # Copy/move file to target location
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if analysis.needs_conversion:
            shutil.move(str(final_source), str(target_path))
        else:
            shutil.copy2(str(final_source), str(target_path))
        
        # Generate metadata files
        self._generate_metadata_files(target_path, final_datatype, suffix, entities, metadata, source_path)
        
        return {
            'success': True,
            'target_path': target_path,
            'datatype': final_datatype,
            'entities': entities,
            'suffix': suffix,
            'converted': analysis.needs_conversion,
            'converter_used': analysis.converter_name
        }
    
    def _validate_entities_for_suffix(self, entities: Dict[str, str], datatype: str, suffix: str):
        """
        Validate entities using suffix-specific requirements from BIDS schema.
        
        This finds the correct sub-rule for the given suffix and validates
        based on that sub-rule's requirements, not broad datatype aggregation.
        """
        # Get the raw schema data to access sub-rules
        raw_schema = self.schema._raw_schema
        datatype_rule = raw_schema.get('rules', {}).get('files', {}).get('raw', {}).get(datatype)
        
        if not datatype_rule:
            # Fallback to minimal validation if no rule found
            if 'sub' not in entities:
                raise ValueError(f"Required entity 'sub' missing for {datatype} suffix '{suffix}'")
            return
        
        # Find which sub-rule contains this suffix
        matching_subrule = None
        for subrule_name, subrule in datatype_rule.items():
            if isinstance(subrule, dict) and 'suffixes' in subrule:
                if suffix in subrule['suffixes']:
                    matching_subrule = subrule
                    break
        
        if not matching_subrule:
            # Suffix not found in any sub-rule, use minimal validation
            if 'sub' not in entities:
                raise ValueError(f"Required entity 'sub' missing for {datatype} suffix '{suffix}'")
            return
        
        # Validate based on the matching sub-rule's requirements
        subrule_entities = matching_subrule.get('entities', {})
        
        # Check required entities for this specific sub-rule
        for entity_name, requirement in subrule_entities.items():
            if requirement == 'required':
                # Map schema entity name to BIDS key
                entity_key = self._map_entity_name_to_key(entity_name)
                if entity_key not in entities:
                    raise ValueError(f"Required entity '{entity_key}' missing for {datatype} suffix '{suffix}'")
        
        # Validate that provided entities are allowed for this specific sub-rule
        subrule_allowed_entities = set(subrule_entities.keys())
        for entity_key in entities:
            entity_name = self._map_entity_key_to_name(entity_key)
            # 'subject' is always implicitly allowed (required for all BIDS files)
            if entity_name != 'subject' and entity_name not in subrule_allowed_entities:
                raise ValueError(f"Entity '{entity_key}' not allowed for {datatype} suffix '{suffix}'")
    
    def get_required_entities_for_suffix(self, datatype: str, suffix: str) -> List[str]:
        """
        Get required entities for a specific datatype/suffix combination.
        
        This uses the same schema traversal logic as _validate_entities_for_suffix
        but returns the required entity keys instead of validating them.
        """
        # Get the raw schema data to access sub-rules
        raw_schema = self.schema._raw_schema
        datatype_rule = raw_schema.get('rules', {}).get('files', {}).get('raw', {}).get(datatype)
        
        if not datatype_rule:
            return ['sub']  # Fallback to minimal requirement
        
        # Find which sub-rule contains this suffix
        matching_subrule = None
        for subrule_name, subrule in datatype_rule.items():
            if isinstance(subrule, dict) and 'suffixes' in subrule:
                if suffix in subrule['suffixes']:
                    matching_subrule = subrule
                    break
        
        if not matching_subrule:
            return ['sub']  # Fallback if no matching rule
        
        # Extract required entities from the matching sub-rule
        required_entities = ['sub']  # Subject always required
        subrule_entities = matching_subrule.get('entities', {})
        
        for entity_name, requirement in subrule_entities.items():
            if requirement == 'required':
                # Map schema entity name to BIDS key
                entity_key = self._map_entity_name_to_key(entity_name)
                if entity_key not in required_entities:
                    required_entities.append(entity_key)
        
        return required_entities
    
    def _map_entity_key_to_name(self, entity_key: str) -> str:
        """Map BIDS entity key to schema entity name using schema data."""
        # Handle special cases: BIDS key to raw schema name
        if entity_key == 'sub':
            return 'subject'
        elif entity_key == 'ses':
            return 'session'
        elif entity_key == 'acq':
            return 'acquisition'
        elif entity_key == 'rec':
            return 'reconstruction'
        elif entity_key == 'ce':
            return 'ceagent'
            
        # Use schema's entity definitions to get proper mapping
        for entity_name, entity_def in self.schema.entities.items():
            if hasattr(entity_def, 'key') and entity_def.key == entity_key:
                return entity_name
        
        # If not found in schema, return the key as-is (might be the same)
        return entity_key
    
    def _map_entity_name_to_key(self, entity_name: str) -> str:
        """Map schema entity name to BIDS entity key using schema data."""
        # Handle special cases: raw schema entity names to BIDS keys
        if entity_name == 'subject':
            return 'sub'
        elif entity_name == 'session':
            return 'ses'
        elif entity_name == 'acquisition':
            return 'acq'
        elif entity_name == 'reconstruction':
            return 'rec'
        elif entity_name == 'ceagent':
            return 'ce'
            
        # Use schema's entity definitions to get proper mapping
        entity_def = self.schema.entities.get(entity_name)
        if entity_def and hasattr(entity_def, 'key'):
            return entity_def.key
        
        # Check if the entity_name itself is a key in the entities
        # (for cases where the raw schema uses the key name directly)
        for entity_def in self.schema.entities.values():
            if entity_def.key == entity_name:
                return entity_name
        
        # If not found in schema, return the name as-is (might be the same)
        return entity_name
    
    
    def _convert_file(self, source_path: Path, converter) -> tuple[Path, Dict[str, Any]]:
        """
        Convert file to BIDS-compliant format
        
        Returns:
            Tuple of (converted_path, metadata)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            converted_path = converter.convert(source_path, temp_path)
            
            # Extract converter metadata
            conv_metadata = converter.extract_metadata(source_path)
            
            # Create a persistent copy
            final_path = Path(tempfile.mktemp(suffix=converted_path.suffix))
            shutil.copy2(converted_path, final_path)
            
            return final_path, conv_metadata
    
    def _validate_entities(self, entities: Dict[str, str], datatype_def):
        """Validate entities against schema rules with entity key/name mapping"""
        
        # Map entity keys to schema names for validation
        def map_entity_key_to_name(entity_key: str) -> str:
            """Map BIDS filename entity keys to schema entity names"""
            if entity_key == 'sub':
                return 'subject'
            elif entity_key == 'ses':
                return 'session'
            else:
                return entity_key
        
        # Check required entities (map schema names back to keys)
        for req_entity_name in datatype_def.required_entities:
            # Map schema entity name to BIDS key for checking
            req_entity_key = 'sub' if req_entity_name == 'subject' else ('ses' if req_entity_name == 'session' else req_entity_name)
            if req_entity_key not in entities:
                raise ValueError(f"Required entity '{req_entity_key}' missing for datatype '{datatype_def.name}'")
        
        # Check allowed entities (map keys to names for validation)
        for entity_key in entities:
            entity_name = map_entity_key_to_name(entity_key)
            if entity_name not in datatype_def.allowed_entities:
                raise ValueError(f"Entity '{entity_key}' not allowed for datatype '{datatype_def.name}'")
        
        # Validate entity values using BIDS keys
        for entity_key, entity_value in entities.items():
            if not self.schema.validate_entity_value(entity_key, entity_value):
                raise ValueError(f"Invalid value '{entity_value}' for entity '{entity_key}'")
    
    def _detect_suffix(self, file_path: Path, datatype: str) -> str:
        """Auto-detect BIDS suffix from filename or datatype"""
        filename_lower = file_path.stem.lower()
        dt = self.schema.get_datatype(datatype)
        
        # Try to find suffix in filename
        for suffix in dt.suffixes:
            if suffix.lower() in filename_lower:
                return suffix
        
        # Use default suffix for datatype
        return DEFAULT_SUFFIXES.get(datatype, datatype)
    
    def _build_target_path(self, entities: Dict[str, str], datatype: str, 
                          suffix: str, extension: str) -> Path:
        """Build BIDS-compliant target path"""
        # Build directory structure
        path_parts = [self.dataset_path]
        
        # Subject directory
        path_parts.append(self._format_entity('sub', entities['sub']))
        
        # Session directory (optional)
        if 'ses' in entities:
            path_parts.append(self._format_entity('ses', entities['ses']))
        
        # Datatype directory
        path_parts.append(datatype)
        
        # Build filename using proper entity order
        filename = self._build_bids_filename(entities, suffix, extension)
        path_parts.append(filename)
        
        return Path(*path_parts)
    
    def _build_bids_filename(self, entities: Dict[str, str], suffix: str, extension: str) -> str:
        """Build BIDS-compliant filename with proper entity ordering"""
        filename_parts = []
        
        # Add entities in BIDS-specified order
        for entity_key in ENTITY_ORDER:
            if entity_key in entities:
                filename_parts.append(self._format_entity(entity_key, entities[entity_key]))
        
        # Add any remaining entities not in standard order (shouldn't happen with proper schema)
        remaining_entities = set(entities.keys()) - set(ENTITY_ORDER)
        for entity_key in sorted(remaining_entities):
            filename_parts.append(self._format_entity(entity_key, entities[entity_key]))
        
        # Build final filename
        filename = "_".join(filename_parts)
        if suffix:
            filename = f"{filename}_{suffix}"
        filename = f"{filename}{extension}"
        
        return filename
    
    def _generate_metadata_files(self, data_path: Path, datatype: str, suffix: str,
                                entities: Dict[str, str], user_metadata: Dict[str, Any], source_path: Path = None):
        """Generate BIDS metadata files based on schema requirements"""
        
        # Generate JSON sidecar
        self._generate_json_sidecar(data_path, datatype, suffix, entities, user_metadata)
        
        # Generate datatype-specific files
        if datatype in ['ieeg', 'eeg', 'meg']:
            self._generate_ephys_files(data_path, entities, datatype, source_path)
        elif datatype == 'nirs':
            self._generate_nirs_files(data_path, entities)
    
    def _generate_json_sidecar(self, data_path: Path, datatype: str, suffix: str,
                              entities: Dict[str, str], user_metadata: Dict[str, Any]):
        """Generate JSON sidecar with schema-required and recommended metadata"""
        # Get metadata from schema
        dt = self.schema.get_datatype(datatype)
        metadata_specs = dt.get_all_metadata(suffix)
        required_metadata = metadata_specs.get('required', {})
        recommended_metadata = metadata_specs.get('recommended', {})
        
        # Start with empty metadata
        json_metadata = {}
        
        # Add user-provided metadata (highest priority)
        json_metadata.update(user_metadata)
        
        # Add subject-level optional metadata
        json_metadata.update(self.optional_metadata)
        
        # Ensure required fields exist (add defaults if missing)
        for field_name, field_spec in required_metadata.items():
            if field_name not in json_metadata:
                json_metadata[field_name] = self._get_default_metadata_value(
                    field_name, field_spec, entities, datatype, suffix
                )
        
        # Add recommended fields with defaults if missing
        for field_name, field_spec in recommended_metadata.items():
            if field_name not in json_metadata:
                default_value = self._get_default_metadata_value(
                    field_name, field_spec, entities, datatype, suffix
                )
                # Only add field if default value is not None (None means omit field)
                if default_value is not None:
                    json_metadata[field_name] = default_value
        
        # Write JSON file if there's metadata to write
        if json_metadata:
            json_path = data_path.with_suffix('.json')
            with open(json_path, 'w') as f:
                json.dump(json_metadata, f, indent=2, sort_keys=True)
    
    def _get_default_metadata_value(self, field_name: str, field_spec: Dict[str, Any],
                                   entities: Dict[str, str], datatype: str = None, suffix: str = None) -> Any:
        """Get appropriate default value for metadata field"""
        # field_spec could be used for type-specific defaults in the future
        _ = field_spec
        
        # Special cases for known fields from BIDS validation warnings
        if field_name == 'SubjectArtefactDescription':
            # For iEEG data, default to "n/a" indicating absence of major artifacts except cardiac and blinks
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        elif field_name == 'iEEGPlacementScheme':
            # iEEG electrode placement description
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        elif field_name == 'iEEGElectrodeGroups':
            # iEEG electrode grouping description
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        elif field_name == 'iEEGGround':
            # iEEG ground electrode description
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        elif field_name.endswith('ChannelCount'):
            # Channel count fields should default to 0 (numeric)
            return 0
        elif field_name in ['EpochLength', 'RecordingDuration']:
            # Duration/length fields should be numeric - but for continuous recordings, 
            # EpochLength should be omitted rather than set to a default
            # Return None to indicate field should be omitted
            return None
        elif field_name == 'StimulusPresentation':
            # Default stimulus presentation information
            return {
                "OperatingSystem": "unknown",
                "SoftwareName": "unknown",
                "SoftwareVersion": "unknown"
            }
        elif field_name == 'TaskName':
            return entities.get('task', DEFAULT_METADATA_VALUES['UNKNOWN'])
        elif field_name == 'HEDVersion':
            # HEDVersion field format is defined in BIDS schema but no default value is provided
            # The BIDS spec requires this field when HED tags are used but leaves version choice to users
            # We use a stable, widely-compatible HED schema version as a reasonable default
            return self._get_default_hed_version()
        elif field_name in ['SamplingFrequency', 'PowerLineFrequency']:
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        elif field_name.endswith('Reference'):
            return DEFAULT_METADATA_VALUES['UNKNOWN']
        elif 'Coordinate' in field_name:
            return DEFAULT_METADATA_VALUES['UNKNOWN']
        else:
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
    
    def _get_default_hed_version(self) -> str:
        """
        Get a default HED schema version that's compatible with current BIDS version.
        
        The BIDS schema defines HEDVersion format but provides no default value.
        We select a stable HED version that's known to work with BIDS v1.10.0.
        
        Returns:
            str: HED schema version string in format required by BIDS
        """
        # HED 8.2.0 is a stable version compatible with BIDS 1.10.0
        # This follows the hed_version format defined in the BIDS schema
        return "8.2.0"
    
    def _generate_ephys_files(self, data_path: Path, entities: Dict[str, str], datatype: str, source_path: Path = None):
        """Generate channels.tsv and events.tsv for electrophysiology data using schema-driven extraction"""
        # Import here to avoid circular imports
        from ..services.BidsMetadataExtractorService import BidsMetadataExtractor
        
        data_dir = data_path.parent
        
        # Initialize metadata extractor
        metadata_extractor = BidsMetadataExtractor()
        
        # Determine source file for extraction 
        if source_path and source_path.exists():
            # Use the original source path if provided
            source_file = source_path
            print(f"Using original source file for TSV extraction: {source_file}")
        else:
            # Fallback: try to find source file that was used to create this data file
            source_file = None
            
            # Check for TRC source files (most common case)
            potential_sources = [
                data_path.with_suffix('.trc'),  # Same name, different extension
                data_path.with_suffix('.TRC'),
            ]
            
            for potential_source in potential_sources:
                if potential_source.exists():
                    source_file = potential_source
                    break
            
            # If we can't find source file, use the data file itself for extraction
            if source_file is None:
                source_file = data_path
                print(f"No source file found, using data file for TSV extraction: {source_file}")
        
        # Generate channels.tsv using proper BIDS filename construction
        channels_filename = self._build_bids_filename(entities, 'channels', '.tsv')
        channels_path = data_dir / channels_filename
        if not channels_path.exists():
            try:
                channels_df = metadata_extractor.extract_channels_tsv(source_file, datatype)
                
                # Validate generated DataFrame
                is_valid, errors = metadata_extractor.validate_generated_tsv(channels_df, 'channels', datatype)
                if not is_valid:
                    print(f"Warning: Generated channels.tsv has validation errors: {errors}")
                
                channels_df.to_csv(channels_path, sep='\t', index=False)
                print(f"Generated schema-compliant channels.tsv with {len(channels_df)} channels")
                
            except Exception as e:
                print(f"Error generating channels.tsv: {e}")
                # Fallback to generic generation
                channels_df = self._create_channels_dataframe_fallback(datatype)
                channels_df.to_csv(channels_path, sep='\t', index=False)
        
        # Generate events.tsv using proper BIDS filename construction  
        events_filename = self._build_bids_filename(entities, 'events', '.tsv')
        events_path = data_dir / events_filename
        if not events_path.exists():
            try:
                events_df = metadata_extractor.extract_events_tsv(source_file, datatype)
                
                # Validate generated DataFrame
                is_valid, errors = metadata_extractor.validate_generated_tsv(events_df, 'events', datatype)
                if not is_valid:
                    print(f"Warning: Generated events.tsv has validation errors: {errors}")
                
                events_df.to_csv(events_path, sep='\t', index=False)
                print(f"Generated schema-compliant events.tsv with {len(events_df)} events")
                
            except Exception as e:
                print(f"Error generating events.tsv: {e}")
                # Fallback to empty events file
                events_df = self._create_events_dataframe_fallback()
                events_df.to_csv(events_path, sep='\t', index=False)
        
        # Generate events.json companion file 
        self._generate_events_json(events_path, entities, datatype)
        
        # Generate electrodes.tsv (required for iEEG data)
        if datatype == 'ieeg':
            # Use schema-driven approach with inheritance awareness
            # If data files are session-specific, electrodes should be too for proper inheritance
            electrodes_entities = self._get_inheritance_aware_entities(entities, datatype, 'electrodes')
            
            # Use schema-driven directory selection based on inheritance-aware entities
            electrodes_dir = self._get_directory_for_entities(electrodes_entities, datatype)
            
            electrodes_filename = self._build_bids_filename(electrodes_entities, 'electrodes', '.tsv')
            electrodes_path = electrodes_dir / electrodes_filename
            if not electrodes_path.exists():
                try:
                    electrodes_df = metadata_extractor.extract_electrodes_tsv(source_file, datatype)
                    
                    # Validate generated DataFrame
                    is_valid, errors = metadata_extractor.validate_generated_tsv(electrodes_df, 'electrodes', datatype)
                    if not is_valid:
                        print(f"Warning: Generated electrodes.tsv has validation errors: {errors}")
                    
                    electrodes_df.to_csv(electrodes_path, sep='\t', index=False)
                    print(f"Generated schema-compliant electrodes.tsv with {len(electrodes_df)} electrodes")
                    
                except Exception as e:
                    print(f"Error generating electrodes.tsv: {e}")
                    # Fallback to empty electrodes file with required structure
                    electrodes_df = self._create_electrodes_dataframe_fallback()
                    electrodes_df.to_csv(electrodes_path, sep='\t', index=False)
                    print(f"Generated fallback electrodes.tsv")
            
            # Generate coordsystem.json (required when electrodes.tsv is present)
            # Use same inheritance-aware entities as electrodes for consistency
            coordsystem_entities = self._get_inheritance_aware_entities(entities, datatype, 'coordsystem')
            coordsystem_dir = self._get_directory_for_entities(coordsystem_entities, datatype)
            
            coordsystem_filename = self._build_bids_filename(coordsystem_entities, 'coordsystem', '.json')
            coordsystem_path = coordsystem_dir / coordsystem_filename
            if not coordsystem_path.exists():
                coordsystem_metadata = self._create_coordsystem_metadata()
                with open(coordsystem_path, 'w') as f:
                    json.dump(coordsystem_metadata, f, indent=2, sort_keys=True)
                print(f"Generated required coordsystem.json for iEEG electrodes")
    
    def _filter_entities_for_suffix(self, entities: Dict[str, str], datatype: str, suffix: str) -> Dict[str, str]:
        """
        Filter entities based on schema requirements for specific datatype/suffix.
        
        This schema-driven method ensures we only include entities that are
        required for the specific suffix, preventing BIDS warnings about
        excessive specificity (e.g., task/acq in electrodes.tsv).
        
        Args:
            entities: Full entity dictionary
            datatype: BIDS datatype (e.g., 'ieeg', 'eeg')  
            suffix: BIDS suffix (e.g., 'electrodes', 'channels', 'events')
            
        Returns:
            Filtered entities containing only schema-required entities
        """
        try:
            # Query schema for required entities for this specific suffix
            required_entities = self.get_required_entities_for_suffix(datatype, suffix)
            
            # Filter entities to include only those required by schema
            filtered_entities = {key: value for key, value in entities.items() 
                               if key in required_entities}
            
            return filtered_entities
            
        except Exception as e:
            # Fallback: if schema query fails, use original entities
            print(f"Warning: Could not filter entities for {datatype}/{suffix}: {e}")
            return entities
    
    def _get_directory_for_entities(self, entities: Dict[str, str], datatype: str) -> Path:
        """
        Get appropriate directory path based on entities using schema-driven logic.
        
        BIDS specification requires:
        - Files with session entities go in session directories
        - Files without session entities go at subject level
        
        Args:
            entities: Filtered entities dictionary
            datatype: BIDS datatype (e.g., 'ieeg', 'eeg')
            
        Returns:
            Path to the appropriate directory
        """
        # Start with subject path
        directory_path = self.subject_path
        
        # Add session directory if session entity is present
        if 'ses' in entities:
            session_dir = self._format_entity('ses', entities['ses'])
            directory_path = directory_path / session_dir
        
        # Add datatype directory
        directory_path = directory_path / datatype
        
        # Ensure directory exists
        directory_path.mkdir(parents=True, exist_ok=True)
        
        return directory_path
    
    def _get_inheritance_aware_entities(self, data_entities: Dict[str, str], datatype: str, suffix: str) -> Dict[str, str]:
        """
        Get entities for metadata files considering BIDS inheritance principle.
        
        For proper inheritance, metadata files (like electrodes.tsv) should be placed
        at the same level or higher than the data files they describe. This means:
        - If data files are session-specific, electrodes should be session-specific
        - If data files are subject-level, electrodes can be subject-level
        
        Args:
            data_entities: Entities from the data file that needs metadata
            datatype: BIDS datatype (e.g., 'ieeg')
            suffix: Metadata suffix (e.g., 'electrodes', 'coordsystem')
            
        Returns:
            Entities for metadata file ensuring proper inheritance
        """
        # Start with schema requirements for this suffix
        schema_required = self._filter_entities_for_suffix(data_entities, datatype, suffix)
        
        # For inheritance-critical files, preserve session context when data is session-specific
        inheritance_critical_suffixes = ['electrodes', 'coordsystem']
        
        if suffix in inheritance_critical_suffixes:
            # If data file has session and subject, keep both for proper inheritance
            if 'ses' in data_entities and 'sub' in data_entities:
                return {
                    'sub': data_entities['sub'],
                    'ses': data_entities['ses']
                }
        
        # Use schema-only filtering for other cases
        return schema_required
    
    def _create_channels_dataframe(self, datatype: str, channel_count: int) -> pd.DataFrame:
        """Create channels dataframe with appropriate structure (legacy method)"""
        return self._create_channels_dataframe_fallback(datatype, channel_count)
    
    def _create_channels_dataframe_fallback(self, datatype: str, channel_count: int = None) -> pd.DataFrame:
        """Fallback method for creating generic channels dataframe"""
        if channel_count is None:
            channel_count = DEFAULT_CHANNEL_COUNTS.get(datatype, 64)
            
        channel_type = 'SEEG' if datatype == 'ieeg' else datatype.upper()
        
        return pd.DataFrame({
            'name': [f'CH{i:03d}' for i in range(1, channel_count + 1)],
            'type': [channel_type] * channel_count,
            'units': ['µV'] * channel_count,
            'sampling_frequency': [DEFAULT_METADATA_VALUES['NOT_AVAILABLE']] * channel_count,
            'status': [DEFAULT_METADATA_VALUES['GOOD_STATUS']] * channel_count
        })
    
    def _create_events_dataframe(self) -> pd.DataFrame:
        """Create empty events dataframe with proper structure (legacy method)"""
        return self._create_events_dataframe_fallback()
    
    def _create_events_dataframe_fallback(self) -> pd.DataFrame:
        """Fallback method for creating empty events dataframe"""
        return pd.DataFrame({
            'onset': [],
            'duration': [],
            'trial_type': [],
            'response_time': [],
            'value': []
        })
    
    def _create_electrodes_dataframe_fallback(self) -> pd.DataFrame:
        """Fallback method for creating minimal electrodes dataframe for iEEG"""
        # BIDS requires at least the 'name' column for electrodes.tsv
        # Other columns are optional but recommended
        return pd.DataFrame({
            'name': [],
            'x': [],
            'y': [],
            'z': [],
            'size': [],
            'hemisphere': [],
            'group': []
        })
    
    def _create_coordsystem_metadata(self) -> Dict[str, Any]:
        """Create BIDS-compliant coordsystem.json metadata for iEEG electrodes"""
        # According to BIDS spec, when electrodes.tsv is present, coordsystem.json is required
        # Since TRC files typically don't contain electrode position information,
        # we provide a minimal compliant structure indicating positions are not available
        return {
            "iEEGCoordinateSystem": "Other",
            "iEEGCoordinateUnits": "n/a", 
            "iEEGCoordinateProcessingDescription": "Electrode positions not available in source TRC file. "
                                                  "Positions should be added manually from imaging data or "
                                                  "surgical planning systems.",
            "iEEGCoordinateProcessingReference": "n/a",
            "iEEGCoordinateSystemDescription": "No coordinate system specified. Electrode positions in "
                                             "electrodes.tsv are empty and should be populated with "
                                             "actual coordinates from MRI, CT, or surgical planning data."
        }
    
    def _generate_events_json(self, events_tsv_path: Path, entities: Dict[str, str], datatype: str):
        """Generate events.json companion file with column definitions and recommended metadata"""
        # Create JSON path by replacing .tsv with .json
        events_json_path = events_tsv_path.with_suffix('.json')
        
        # Read the events.tsv file to get column names
        try:
            events_df = pd.read_csv(events_tsv_path, sep='\t')
            column_names = events_df.columns.tolist()
        except Exception:
            # Fallback to default columns if TSV can't be read
            column_names = ['onset', 'duration', 'trial_type', 'response_time', 'value']
        
        # Create events.json metadata
        events_metadata = {}
        
        # Add StimulusPresentation (recommended field that was missing)
        events_metadata['StimulusPresentation'] = self._get_default_metadata_value(
            'StimulusPresentation', {}, entities, datatype, 'events'
        )
        
        # Define columns present in the TSV, but only define non-standard columns
        # Standard BIDS columns (onset, duration, trial_type, response_time) are predefined by the spec
        # and should not be redefined to avoid TSV_COLUMN_TYPE_REDEFINED warnings
        standard_bids_columns = ['onset', 'duration', 'trial_type', 'response_time']
        
        # Check if dataset has HED columns and add HEDVersion if needed
        has_hed_column = 'HED' in column_names
        if has_hed_column and 'HEDVersion' not in events_metadata:
            # Add HEDVersion field when HED columns are present (required by BIDS spec)
            events_metadata['HEDVersion'] = self._get_default_hed_version()
        
        for column in column_names:
            if column not in standard_bids_columns:
                # Properly handle HED column by defining it in events.json
                if column == 'HED':
                    events_metadata['HED'] = {
                        "Description": "Hierarchical Event Descriptor (HED) tags for event annotation."
                    }
                # Only define non-standard columns to avoid type redefinition warnings
                elif column == 'value':
                    events_metadata['value'] = {
                        "Description": "Marker value associated with the event (for example, the value of a trigger sent to the acquisition system)."
                    }
                else:
                    # Generic description for other non-standard columns
                    events_metadata[column] = {
                        "Description": f"Column {column} in events file."
                    }
        
        # Write events.json file
        with open(events_json_path, 'w') as f:
            json.dump(events_metadata, f, indent=2, sort_keys=True)
        print(f"Generated events.json companion file with {len(column_names)} column definitions")
    
    def _generate_nirs_files(self, data_path: Path, entities: Dict[str, str]):
        """Generate NIRS-specific files (optodes.tsv, etc.)"""
        # entities parameter could be used for entity-specific metadata in the future
        _ = entities
        
        base_name = data_path.with_suffix('').name
        data_dir = data_path.parent
        
        # Generate optodes.tsv
        optodes_path = data_dir / f"{base_name}_optodes.tsv"
        if not optodes_path.exists():
            optodes_df = pd.DataFrame({
                'name': [],
                'type': [],
                'x': [],
                'y': [],
                'z': []
            })
            optodes_df.to_csv(optodes_path, sep='\t', index=False)
    
    def rename_subject(self, new_subject_id: str):
        """Rename subject and update all associated files"""
        # Validate new subject ID
        if not self.schema.validate_entity_value('sub', new_subject_id):
            raise ValueError(f"Invalid new subject ID '{new_subject_id}' according to BIDS schema")
        
        if new_subject_id == self.subject_id:
            return  # Nothing to do
        
        old_subject_path = self.subject_path
        old_subject_formatted = self._format_entity('sub', self.subject_id)
        new_subject_formatted = self._format_entity('sub', new_subject_id)
        new_subject_path = self.dataset_path / new_subject_formatted
        
        # Rename all files within the subject directory
        for file_path in old_subject_path.rglob('*'):
            if file_path.is_file():
                old_name = file_path.name
                new_name = old_name.replace(old_subject_formatted, new_subject_formatted)
                if old_name != new_name:
                    file_path.rename(file_path.parent / new_name)
        
        # Rename subject directory
        old_subject_path.rename(new_subject_path)
        
        # Update instance variables
        self.subject_id = new_subject_id
        self.subject_path = new_subject_path
    
    def list_files(self, datatype: Optional[str] = None, 
                  session: Optional[str] = None) -> List[Path]:
        """List files for this subject"""
        search_path = self.subject_path
        
        if session:
            search_path = search_path / self._format_entity('ses', session)
        
        if datatype:
            search_path = search_path / datatype
        
        if not search_path.exists():
            return []
        
        # Find all data files (not JSON/TSV metadata)
        data_files = []
        for ext in BIDS_DATA_EXTENSIONS:
            data_files.extend(search_path.rglob(f'*{ext}'))
        
        return sorted(data_files)
    
    def get_sessions(self) -> List[str]:
        """Get list of sessions for this subject"""
        sessions = []
        for item in self.subject_path.iterdir():
            if item.is_dir() and item.name.startswith('ses-'):
                sessions.append(item.name.replace('ses-', ''))
        return sorted(sessions)
    
    def get_datatypes(self, session: Optional[str] = None) -> List[str]:
        """Get list of datatypes for this subject"""
        if session:
            search_path = self.subject_path / self._format_entity('ses', session)
        else:
            search_path = self.subject_path
        
        if not search_path.exists():
            return []
        
        datatypes = []
        for item in search_path.iterdir():
            if item.is_dir() and item.name in self.schema.datatypes:
                datatypes.append(item.name)
        
        return sorted(datatypes)
    
    def set_subject_id(self, new_subject_id: str):
        """
        Set a new subject ID for the BidsSubject instance.
        This method updates the subject ID and renames the subject folder and all files recursively with the new subject ID.

        Args:
            new_subject_id (str): The new subject ID to be set (without 'sub-' prefix).
        """
        import os
        
        # Check if the new subject ID is different from the current one
        if new_subject_id != self.subject_id:
            old_subject_id = self.subject_id
            old_folder_name = f"sub-{old_subject_id}"
            new_folder_name = f"sub-{new_subject_id}"
            
            # Current subject path
            old_subject_path = self.subject_path
            new_subject_path = self.dataset_path / new_folder_name
            
            try:
                # Rename all files recursively with the new subject ID
                if old_subject_path.exists():
                    for root, dirs, files in os.walk(old_subject_path):
                        for file in files:
                            if old_folder_name in file:
                                old_file_path = os.path.join(root, file)
                                new_file_name = file.replace(old_folder_name, new_folder_name)
                                new_file_path = os.path.join(root, new_file_name)
                                try:
                                    os.rename(old_file_path, new_file_path)
                                except OSError as e:
                                    print(f"Error renaming file {old_file_path} to {new_file_path}: {e}")
                                    raise
                    
                    # Rename the subject folder itself
                    try:
                        os.rename(str(old_subject_path), str(new_subject_path))
                    except OSError as e:
                        print(f"Error renaming folder {old_subject_path} to {new_subject_path}: {e}")
                        raise
                    
                    # Update the internal state
                    self.subject_id = new_subject_id
                    self.subject_path = new_subject_path
                else:
                    print(f"Warning: Subject path does not exist: {old_subject_path}")
            except Exception as e:
                print(f"Error in set_subject_id: {e}")
                raise