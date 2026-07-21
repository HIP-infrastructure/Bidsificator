"""File placement for a BidsSubject.

`SubjectFileWriter` owns the ``add_file`` pipeline: analyze the source file,
convert it if needed, auto-detect the suffix, validate the entities against the
schema, build the BIDS-compliant target path, and copy/move the data file into
place. Generating the accompanying sidecars/TSVs is delegated to
`SubjectSidecarGenerator` (reached through the owning subject).
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any

from bidsificator.core.bids_constants import get_default_suffix_for_datatype
from bidsificator.core.file_analysis import FileAnalysis
from bidsificator.core.subject_component import SubjectComponent


class SubjectFileWriter(SubjectComponent):
    """Adds files to a BidsSubject with conversion and schema-driven naming."""

    def analyze_file(self, source_path: Path, target_format: str | None = None) -> FileAnalysis:
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
                 entities: dict[str, str] | None = None,
                 suffix: str | None = None,
                 metadata: dict[str, Any] | None = None,
                 target_format: str | None = None) -> dict[str, Any]:
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
            # Prioritize explicit datatype parameter over auto-detection
            final_datatype = datatype or analysis.bids_datatype
        else:
            final_source = source_path
            # Prioritize explicit datatype parameter over auto-detection
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

        # Generate metadata files (JSON sidecar + companion TSVs)
        self._subject._generate_metadata_files(
            target_path, final_datatype, suffix, entities, metadata, source_path
        )

        return {
            'success': True,
            'target_path': target_path,
            'datatype': final_datatype,
            'entities': entities,
            'suffix': suffix,
            'converted': analysis.needs_conversion,
            'converter_used': analysis.converter_name
        }

    def _validate_entities_for_suffix(self, entities: dict[str, str], datatype: str, suffix: str):
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
        for _subrule_name, subrule in datatype_rule.items():
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

    def get_required_entities_for_suffix(self, datatype: str, suffix: str) -> list[str]:
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
        for _subrule_name, subrule in datatype_rule.items():
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

    def _convert_file(self, source_path: Path, converter) -> tuple[Path, dict[str, Any]]:
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

    def _validate_entities(self, entities: dict[str, str], datatype_def):
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
            req_entity_key = (
                'sub' if req_entity_name == 'subject'
                else ('ses' if req_entity_name == 'session' else req_entity_name)
            )
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

        # Use schema-driven default suffix for datatype
        return get_default_suffix_for_datatype(datatype)

    def _build_target_path(self, entities: dict[str, str], datatype: str,
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

    def _build_bids_filename(self, entities: dict[str, str], suffix: str, extension: str) -> str:
        """Build BIDS-compliant filename using schema-driven FilenameBuilder"""
        return self.filename_builder.build_filename(
            entities=entities,
            suffix=suffix,
            extension=extension,
            validate=False  # Skip validation for internal use (already validated)
        )
