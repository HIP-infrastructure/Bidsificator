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
        
        # Validate subject ID using schema
        if not self.schema.validate_entity_value('sub', subject_id):
            raise ValueError(f"Invalid subject ID '{subject_id}' according to BIDS schema")
        
        self.subject_path = self._build_subject_path()
        self.subject_path.mkdir(parents=True, exist_ok=True)
        
        # Create default BIDS folder structure (matching old behavior)
        self._create_default_folders()
        
        # Initialize converter registry
        self.converter_registry = ConverterRegistry()
        
        # Track optional metadata for this subject
        self.optional_metadata: Dict[str, Any] = {}
    
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
        self._generate_metadata_files(target_path, final_datatype, suffix, entities, metadata)
        
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
                                entities: Dict[str, str], user_metadata: Dict[str, Any]):
        """Generate BIDS metadata files based on schema requirements"""
        
        # Generate JSON sidecar
        self._generate_json_sidecar(data_path, datatype, suffix, entities, user_metadata)
        
        # Generate datatype-specific files
        if datatype in ['ieeg', 'eeg', 'meg']:
            self._generate_ephys_files(data_path, entities, datatype)
        elif datatype == 'nirs':
            self._generate_nirs_files(data_path, entities)
    
    def _generate_json_sidecar(self, data_path: Path, datatype: str, suffix: str,
                              entities: Dict[str, str], user_metadata: Dict[str, Any]):
        """Generate JSON sidecar with schema-required metadata"""
        # Get required metadata from schema
        dt = self.schema.get_datatype(datatype)
        required_metadata = dt.metadata_requirements.get('required', {})
        
        # suffix parameter could be used for suffix-specific metadata in the future
        _ = suffix
        
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
                    field_name, field_spec, entities
                )
        
        # Write JSON file if there's metadata to write
        if json_metadata:
            json_path = data_path.with_suffix('.json')
            with open(json_path, 'w') as f:
                json.dump(json_metadata, f, indent=2, sort_keys=True)
    
    def _get_default_metadata_value(self, field_name: str, field_spec: Dict[str, Any],
                                   entities: Dict[str, str]) -> Any:
        """Get appropriate default value for metadata field"""
        # field_spec could be used for type-specific defaults in the future
        _ = field_spec
        
        # Special cases for known fields
        if field_name == 'TaskName':
            return entities.get('task', DEFAULT_METADATA_VALUES['UNKNOWN'])
        elif field_name in ['SamplingFrequency', 'PowerLineFrequency']:
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        elif field_name.endswith('Reference'):
            return DEFAULT_METADATA_VALUES['UNKNOWN']
        elif 'Coordinate' in field_name:
            return DEFAULT_METADATA_VALUES['UNKNOWN']
        else:
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
    
    def _generate_ephys_files(self, data_path: Path, entities: Dict[str, str], datatype: str):
        """Generate channels.tsv and events.tsv for electrophysiology data"""
        # entities parameter could be used for entity-specific metadata in the future
        _ = entities
        
        base_name = data_path.with_suffix('').name
        data_dir = data_path.parent
        
        # Determine channel count from configuration
        channel_count = DEFAULT_CHANNEL_COUNTS.get(datatype, 64)
        
        # Generate channels.tsv
        channels_path = data_dir / f"{base_name}_channels.tsv"
        if not channels_path.exists():
            channels_df = self._create_channels_dataframe(datatype, channel_count)
            channels_df.to_csv(channels_path, sep='\t', index=False)
        
        # Generate events.tsv
        events_path = data_dir / f"{base_name}_events.tsv"
        if not events_path.exists():
            events_df = self._create_events_dataframe()
            events_df.to_csv(events_path, sep='\t', index=False)
    
    def _create_channels_dataframe(self, datatype: str, channel_count: int) -> pd.DataFrame:
        """Create channels dataframe with appropriate structure"""
        channel_type = 'SEEG' if datatype == 'ieeg' else datatype.upper()
        
        return pd.DataFrame({
            'name': [f'CH{i:03d}' for i in range(1, channel_count + 1)],
            'type': [channel_type] * channel_count,
            'units': ['µV'] * channel_count,
            'sampling_frequency': [DEFAULT_METADATA_VALUES['NOT_AVAILABLE']] * channel_count,
            'status': [DEFAULT_METADATA_VALUES['GOOD_STATUS']] * channel_count
        })
    
    def _create_events_dataframe(self) -> pd.DataFrame:
        """Create empty events dataframe with proper structure"""
        return pd.DataFrame({
            'onset': [],
            'duration': [],
            'trial_type': [],
            'response_time': [],
            'value': []
        })
    
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