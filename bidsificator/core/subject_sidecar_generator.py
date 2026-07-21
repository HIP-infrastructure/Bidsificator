"""Sidecar and companion-file generation for a BidsSubject.

`SubjectSidecarGenerator` produces the metadata that accompanies a data file:
the JSON sidecar (with schema-required/recommended fields and sensible
defaults), the electrophysiology companions (channels.tsv, events.tsv/.json,
electrodes.tsv, coordsystem.json) and the NIRS optodes.tsv. It is driven by
`SubjectFileWriter.add_file`, which reaches it through the owning subject once
the data file is in place.
"""

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from bidsificator.core.bids_constants import (
    DEFAULT_CHANNEL_COUNTS,
    DEFAULT_METADATA_VALUES,
)
from bidsificator.core.subject_component import SubjectComponent

logger = logging.getLogger(__name__)


class SubjectSidecarGenerator(SubjectComponent):
    """Generates JSON sidecars and companion TSV/JSON files for a BidsSubject."""

    def _generate_metadata_files(self, data_path: Path, datatype: str, suffix: str,
                                entities: dict[str, str], user_metadata: dict[str, Any], source_path: Path = None):
        """Generate BIDS metadata files based on schema requirements"""

        # Generate JSON sidecar
        self._generate_json_sidecar(data_path, datatype, suffix, entities, user_metadata)

        # Generate datatype-specific files
        if datatype in ['ieeg', 'eeg', 'meg']:
            self._generate_ephys_files(data_path, entities, datatype, source_path)
        elif datatype == 'nirs':
            self._generate_nirs_files(data_path, entities)

    def _generate_json_sidecar(self, data_path: Path, datatype: str, suffix: str,
                              entities: dict[str, str], user_metadata: dict[str, Any]):
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
                default_value = self._get_default_metadata_value(
                    field_name, field_spec, entities, datatype, suffix
                )
                # Only add required field if default value is not None
                if default_value is not None:
                    json_metadata[field_name] = default_value

        # Add recommended fields with defaults if missing
        for field_name, field_spec in recommended_metadata.items():
            if field_name not in json_metadata:
                default_value = self._get_default_metadata_value(
                    field_name, field_spec, entities, datatype, suffix
                )
                # Only add field if default value is not None (None means omit field)
                if default_value is not None:
                    json_metadata[field_name] = default_value

        # Final cleanup: Remove any None values that might have been added from user metadata
        json_metadata = {k: v for k, v in json_metadata.items() if v is not None}

        # Write JSON file if there's metadata to write
        if json_metadata:
            json_path = data_path.with_suffix('.json')
            with open(json_path, 'w') as f:
                json.dump(json_metadata, f, indent=2, sort_keys=True)

    def _get_default_metadata_value(self, field_name: str, field_spec: dict[str, Any],
                                   entities: dict[str, str], datatype: str = None, suffix: str = None) -> Any:
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

        # MRI-specific metadata field handling
        elif field_name in ['Manufacturer', 'ManufacturersModelName', 'DeviceSerialNumber', 'StationName']:
            # Equipment identification fields - use 'n/a' when not available from source data
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        elif field_name in [
            'SoftwareVersions', 'PulseSequenceType', 'ScanningSequence',
            'SequenceVariant', 'SequenceName'
        ]:
            # MRI sequence and software information - use 'n/a' when not available
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        elif field_name in ['ReceiveCoilName', 'ReceiveCoilActiveElements', 'MatrixCoilMode', 'CoilCombinationMethod']:
            # MRI coil information - use 'n/a' when not available
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        elif field_name in ['InstitutionName', 'InstitutionAddress', 'InstitutionalDepartmentName']:
            # Institution information - use 'n/a' when not available
            return DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        elif field_name == 'PulseSequenceDetails':
            # Detailed sequence information - provide helpful default
            return "Information not available from source data"
        elif field_name == 'MRAcquisitionType':
            # Default to '3D' for anatomical scans, which is most common
            return "3D"

        # MRI numeric fields with conservative defaults for some
        elif field_name in ['ParallelReductionFactorInPlane', 'ParallelReductionFactorOutOfPlane']:
            # Conservative default: 1 (no parallel imaging acceleration when unknown)
            return 1

        # MRI numeric fields - omit (return None) when not available to avoid type errors
        elif field_name in [
            'MagneticFieldStrength', 'EchoTime', 'FlipAngle', 'DwellTime', 'InversionTime',
            'EffectiveEchoSpacing', 'TotalReadoutTime', 'MixingTime',
            'MTOffsetFrequency', 'MTPulseBandwidth', 'MTNumberOfPulses', 'MTPulseDuration',
            'PartialFourier', 'MultibandAccelerationFactor', 'NumberShots',
            'SpoilingRFPhaseIncrement', 'SpoilingGradientMoment', 'SpoilingGradientDuration'
        ]:
            # Numeric fields - omit when not available (prevents JSON schema validation errors)
            return None

        # MRI boolean fields - conservative defaults for some, omit others
        elif field_name == 'NonlinearGradientCorrection':
            # Conservative default: false (assume no correction when unknown)
            return False
        elif field_name in ['MTState', 'SpoilingState']:
            # Boolean fields - omit when unknown (prevents false/invalid assumptions)
            return None

        # MRI array fields - omit when not available
        elif field_name in ['TablePosition']:
            # Array fields - omit when not available (prevents empty array issues)
            return None

        # MRI enum fields - omit when not available to avoid invalid values
        elif field_name in ['MTPulseShape', 'SpoilingType']:
            # Enum fields - omit when not available (prevents invalid enum values)
            return None

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

    def _generate_ephys_files(self, data_path: Path, entities: dict[str, str], datatype: str, source_path: Path = None):
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
            logger.debug("Using original source file for TSV extraction: %s", source_file)
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
                logger.debug("No source file found, using data file for TSV extraction: %s", source_file)

        # Generate channels.tsv using proper BIDS filename construction
        channels_filename = self._subject._build_bids_filename(entities, 'channels', '.tsv')
        channels_path = data_dir / channels_filename
        if not channels_path.exists():
            try:
                channels_df = metadata_extractor.extract_channels_tsv(source_file, datatype)

                # Validate generated DataFrame
                is_valid, errors = metadata_extractor.validate_generated_tsv(channels_df, 'channels', datatype)
                if not is_valid:
                    logger.warning("Generated channels.tsv has validation errors: %s", errors)

                channels_df.to_csv(channels_path, sep='\t', index=False)
                logger.debug("Generated schema-compliant channels.tsv with %d channels", len(channels_df))

            except Exception:
                logger.exception("Error generating channels.tsv")
                # Fallback to generic generation
                channels_df = self._create_channels_dataframe_fallback(datatype)
                channels_df.to_csv(channels_path, sep='\t', index=False)

        # Generate events.tsv using proper BIDS filename construction
        events_filename = self._subject._build_bids_filename(entities, 'events', '.tsv')
        events_path = data_dir / events_filename
        if not events_path.exists():
            try:
                events_df = metadata_extractor.extract_events_tsv(source_file, datatype)

                # Validate generated DataFrame
                is_valid, errors = metadata_extractor.validate_generated_tsv(events_df, 'events', datatype)
                if not is_valid:
                    logger.warning("Generated events.tsv has validation errors: %s", errors)

                events_df.to_csv(events_path, sep='\t', index=False)
                logger.debug("Generated schema-compliant events.tsv with %d events", len(events_df))

            except Exception:
                logger.exception("Error generating events.tsv")
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

            electrodes_filename = self._subject._build_bids_filename(electrodes_entities, 'electrodes', '.tsv')
            electrodes_path = electrodes_dir / electrodes_filename
            # Regenerate if doesn't exist OR if contact labeling file provided
            if not electrodes_path.exists() or self.contact_labeling_file is not None:
                try:
                    electrodes_df = metadata_extractor.extract_electrodes_tsv(
                        source_file,
                        datatype,
                        contact_labeling_file=self.contact_labeling_file
                    )

                    # Validate generated DataFrame
                    is_valid, errors = metadata_extractor.validate_generated_tsv(electrodes_df, 'electrodes', datatype)
                    if not is_valid:
                        logger.warning("Generated electrodes.tsv has validation errors: %s", errors)

                    electrodes_df.to_csv(electrodes_path, sep='\t', index=False)
                    logger.debug("Generated schema-compliant electrodes.tsv with %d electrodes", len(electrodes_df))

                except Exception:
                    logger.exception("Error generating electrodes.tsv")
                    # Fallback to empty electrodes file with required structure
                    electrodes_df = self._create_electrodes_dataframe_fallback()
                    electrodes_df.to_csv(electrodes_path, sep='\t', index=False)
                    logger.debug("Generated fallback electrodes.tsv")

            # Generate coordsystem.json (required when electrodes.tsv is present)
            # Use same inheritance-aware entities as electrodes for consistency
            coordsystem_entities = self._get_inheritance_aware_entities(entities, datatype, 'coordsystem')
            coordsystem_dir = self._get_directory_for_entities(coordsystem_entities, datatype)

            coordsystem_filename = self._subject._build_bids_filename(coordsystem_entities, 'coordsystem', '.json')
            coordsystem_path = coordsystem_dir / coordsystem_filename
            if not coordsystem_path.exists():
                coordsystem_metadata = self._create_coordsystem_metadata()
                with open(coordsystem_path, 'w') as f:
                    json.dump(coordsystem_metadata, f, indent=2, sort_keys=True)
                logger.debug("Generated required coordsystem.json for iEEG electrodes")

    def _filter_entities_for_suffix(self, entities: dict[str, str], datatype: str, suffix: str) -> dict[str, str]:
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
            required_entities = self._subject.get_required_entities_for_suffix(datatype, suffix)

            # Filter entities to include only those required by schema
            filtered_entities = {key: value for key, value in entities.items()
                               if key in required_entities}

            return filtered_entities

        except Exception as e:
            # Fallback: if schema query fails, use original entities
            logger.warning("could not filter entities for %s/%s: %s", datatype, suffix, e, exc_info=True)
            return entities

    def _get_directory_for_entities(self, entities: dict[str, str], datatype: str) -> Path:
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

    def _get_inheritance_aware_entities(
        self, data_entities: dict[str, str], datatype: str, suffix: str
    ) -> dict[str, str]:
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

    def _create_coordsystem_metadata(self) -> dict[str, Any]:
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

    def _generate_events_json(self, events_tsv_path: Path, entities: dict[str, str], datatype: str):
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
                        "Description": (
                            "Marker value associated with the event (for example, "
                            "the value of a trigger sent to the acquisition system)."
                        )
                    }
                else:
                    # Generic description for other non-standard columns
                    events_metadata[column] = {
                        "Description": f"Column {column} in events file."
                    }

        # Write events.json file
        with open(events_json_path, 'w') as f:
            json.dump(events_metadata, f, indent=2, sort_keys=True)
        logger.debug("Generated events.json companion file with %d column definitions", len(column_names))

    def _generate_nirs_files(self, data_path: Path, entities: dict[str, str]):
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
