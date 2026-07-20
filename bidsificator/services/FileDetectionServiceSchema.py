"""
Schema-driven file detection service with conversion awareness.

Replaces hardcoded file detection with dynamic schema-driven detection
and integrates with the converter registry for file conversion support.
"""

from dataclasses import dataclass
from pathlib import Path

from ..converters.base import FormatConverter
from ..converters.registry import ConverterRegistry
from ..core.schema import BidsSchemaManager


@dataclass
class FileDetectionResult:
    """Result of file detection analysis"""
    source_path: Path
    detected_datatype: str | None
    detected_suffix: str | None
    needs_conversion: bool
    converter: FormatConverter | None
    target_format: str | None
    confidence: float  # 0.0 to 1.0
    reasons: list[str]  # Human-readable reasons for detection


@dataclass
class ModalityInfo:
    """Information about a BIDS modality/datatype"""
    datatype: str
    suffixes: list[str]
    extensions: set[str]
    required_entities: set[str]
    optional_entities: set[str]
    ui_requirements: dict[str, bool]


class FileDetectionService:
    """Schema-driven file detection with conversion awareness."""

    def __init__(self, schema_manager: BidsSchemaManager = None):
        self.schema_manager = schema_manager or BidsSchemaManager.get_instance()
        self.converter_registry = ConverterRegistry()
        self._modality_cache: dict[str, ModalityInfo] = {}

        self._build_modality_cache()

    def _build_modality_cache(self) -> None:
        """Build cache of modality information from schema"""
        for datatype_name, datatype in self.schema_manager.datatypes.items():
            # Get all suffixes for this datatype
            suffixes = []
            extensions = set()

            if hasattr(datatype, 'suffixes') and datatype.suffixes:
                suffixes = list(datatype.suffixes)

            # Get extensions from file registry if available
            if self.schema_manager.file_registry:
                # Get extensions directly for this datatype
                datatype_extensions = self.schema_manager.file_registry.get_supported_extensions(datatype_name)
                extensions.update(datatype_extensions)

            # Get entity requirements from datatype
            required_entities = set()
            optional_entities = set()

            # Look at datatype to determine required vs optional entities
            if hasattr(datatype, 'required_entities') and datatype.required_entities:
                required_entities = set(datatype.required_entities)

            if hasattr(datatype, 'allowed_entities') and datatype.allowed_entities:
                optional_entities = set(datatype.allowed_entities) - required_entities

            # Create UI requirements based on datatype
            ui_requirements = self._get_ui_requirements_for_datatype(datatype_name)

            self._modality_cache[datatype_name] = ModalityInfo(
                datatype=datatype_name,
                suffixes=suffixes,
                extensions=extensions,
                required_entities=required_entities,
                optional_entities=optional_entities,
                ui_requirements=ui_requirements
            )

    def _get_ui_requirements_for_datatype(self, datatype: str) -> dict[str, bool]:
        """Get UI requirements for a specific datatype based on schema"""
        # Default requirements
        requirements = {
            'show_session': True,
            'show_task': False,
            'show_contrast': False,
            'show_acquisition': True,
            'show_reconstruction': False,
            'show_direction': False,
            'show_run': True
        }

        # Adjust based on datatype characteristics
        if datatype in ['func', 'ieeg', 'eeg', 'meg', 'beh']:
            requirements['show_task'] = True
        elif datatype in ['anat', 'dwi']:
            requirements['show_contrast'] = True
            requirements['show_reconstruction'] = True
            requirements['show_direction'] = True
        elif datatype in ['fmap']:
            requirements['show_direction'] = True

        return requirements

    def detect_file(self, file_path: Path, target_format: str = None) -> FileDetectionResult:
        """
        Detect file type and conversion requirements.

        Args:
            file_path: Path to the file to analyze
            target_format: Optional target format preference

        Returns:
            FileDetectionResult with detection analysis
        """
        file_path = Path(file_path)
        reasons = []
        confidence = 0.0

        # Check if file needs conversion
        converter = self.converter_registry.get_converter(file_path, target_format)
        needs_conversion = converter is not None

        if needs_conversion:
            reasons.append(f"File format {file_path.suffix} requires conversion")
            target_fmt = converter.target_format
        else:
            target_fmt = None

        # Detect BIDS datatype and suffix
        detected_datatype, detected_suffix, detection_confidence, detection_reasons = self._detect_bids_info(file_path)

        reasons.extend(detection_reasons)
        confidence = max(confidence, detection_confidence)

        return FileDetectionResult(
            source_path=file_path,
            detected_datatype=detected_datatype,
            detected_suffix=detected_suffix,
            needs_conversion=needs_conversion,
            converter=converter,
            target_format=target_fmt,
            confidence=confidence,
            reasons=reasons
        )

    def _detect_bids_info(self, file_path: Path) -> tuple[str | None, str | None, float, list[str]]:
        """
        Detect BIDS datatype and suffix from file characteristics.

        Returns:
            (datatype, suffix, confidence, reasons)
        """
        filename = file_path.name.lower()
        extension = file_path.suffix.lower()
        stem = file_path.stem.lower()

        reasons = []
        best_datatype = None
        best_suffix = None
        best_confidence = 0.0

        # Handle compound extensions like .nii.gz
        full_extension = extension
        if filename.endswith('.nii.gz'):
            full_extension = '.nii.gz'

        # Try extension-based detection first
        # Use file registry's detection logic which is smarter
        detected_via_registry = None
        if self.schema_manager.file_registry:
            detected_via_registry = self.schema_manager.file_registry.detect_datatype(file_path)

        if detected_via_registry:
            # Use registry detection as primary
            best_datatype = detected_via_registry
            best_confidence = 0.8
            reasons.append(f"File registry detected {detected_via_registry}")

            # Try to find matching suffix
            if detected_via_registry in self._modality_cache:
                modality_info = self._modality_cache[detected_via_registry]
                for suffix in modality_info.suffixes:
                    if suffix.lower() in stem:
                        best_suffix = suffix
                        best_confidence = 0.9
                        reasons.append(f"Suffix {suffix} detected in filename")
                        break

                # Default suffix if none found
                if not best_suffix and modality_info.suffixes:
                    # For ieeg files, prefer 'ieeg' suffix
                    if detected_via_registry == 'ieeg' and 'ieeg' in modality_info.suffixes:
                        best_suffix = 'ieeg'
                    else:
                        best_suffix = modality_info.suffixes[0]
        else:
            # Fallback to extension matching
            for datatype, modality_info in self._modality_cache.items():
                if extension in modality_info.extensions or full_extension in modality_info.extensions:
                    confidence = 0.6  # Lower confidence for basic extension match
                    reasons.append(f"Extension {full_extension} matches {datatype}")

                    # Try to detect suffix from filename
                    for suffix in modality_info.suffixes:
                        if suffix.lower() in stem:
                            confidence = 0.8  # High confidence for suffix + extension match
                            reasons.append(f"Suffix {suffix} detected in filename")

                            if confidence > best_confidence:
                                best_datatype = datatype
                                best_suffix = suffix
                                best_confidence = confidence
                            break

                    # If no suffix match but extension matches
                    if confidence > best_confidence:
                        best_datatype = datatype
                        best_suffix = modality_info.suffixes[0] if modality_info.suffixes else None
                        best_confidence = confidence

        # Fallback: pattern-based detection
        if best_confidence < 0.5:
            fallback_datatype, fallback_suffix, fallback_confidence, fallback_reasons = (
                self._pattern_based_detection(file_path)
            )
            if fallback_confidence > best_confidence:
                best_datatype = fallback_datatype
                best_suffix = fallback_suffix
                best_confidence = fallback_confidence
                reasons.extend(fallback_reasons)

        return best_datatype, best_suffix, best_confidence, reasons

    def _pattern_based_detection(self, file_path: Path) -> tuple[str | None, str | None, float, list[str]]:
        """Fallback pattern-based detection for common file patterns"""
        filename = file_path.name.lower()
        reasons = []

        # Common patterns
        patterns = {
            # Anatomy patterns
            ('anat', 'T1w'): ['t1w', 't1.nii', '_t1_', 'mprage'],
            ('anat', 'T2w'): ['t2w', 't2.nii', '_t2_', 'tse'],
            ('anat', 'FLAIR'): ['flair', '_flair_'],

            # iEEG patterns
            ('ieeg', 'ieeg'): ['_ieeg', '.trc', '.edf', 'micromed'],

            # EEG patterns
            ('eeg', 'eeg'): ['_eeg', '.vhdr', '.bdf'],

            # Functional patterns
            ('func', 'bold'): ['_bold', '_func', 'rest', 'task'],

            # Behavioral patterns
            ('beh', 'events'): ['_events', '.tsv'],
            ('beh', 'physio'): ['_physio', '_cardiac', '_respiratory'],
        }

        best_confidence = 0.0
        best_datatype = None
        best_suffix = None

        for (datatype, suffix), pattern_list in patterns.items():
            for pattern in pattern_list:
                if pattern in filename:
                    confidence = 0.6  # Medium confidence for pattern match
                    reasons.append(f"Pattern '{pattern}' suggests {datatype}/{suffix}")

                    if confidence > best_confidence:
                        best_datatype = datatype
                        best_suffix = suffix
                        best_confidence = confidence

        return best_datatype, best_suffix, best_confidence, reasons

    def get_modality_info(self, datatype: str) -> ModalityInfo | None:
        """Get cached modality information for a datatype"""
        return self._modality_cache.get(datatype)

    def get_all_datatypes(self) -> list[str]:
        """Get list of all available BIDS datatypes"""
        return list(self._modality_cache.keys())

    def get_file_filters(self) -> dict[str, str]:
        """
        Get file filters for different modalities for UI dialogs.

        Returns:
            Dictionary mapping datatype to file filter strings
        """
        filters = {}

        for datatype, modality_info in self._modality_cache.items():
            if modality_info.extensions:
                # Create filter string from extensions
                ext_list = " ".join(f"*{ext}" for ext in sorted(modality_info.extensions))
                filters[f"{datatype}"] = f"{datatype.upper()} files ({ext_list})"

        # Add converter source formats
        converter_formats = self.converter_registry.get_supported_source_formats()
        for ext, _converter_names in converter_formats.items():
            filters[f"convertible_{ext}"] = f"Convertible files ({ext})"

        return filters

    def get_all_supported_extensions(self) -> str:
        """
        Get a filter string for all supported file types (native BIDS + convertible).

        Returns:
            Filter string for QFileDialog with all supported extensions
        """
        # Get all native BIDS extensions
        all_extensions = set()
        for modality_info in self._modality_cache.values():
            all_extensions.update(modality_info.extensions)

        # Add converter source extensions
        for ext_list in self.converter_registry.converters.keys():
            all_extensions.add(ext_list)

        # Format as filter string
        ext_string = " ".join(f"*{ext}" for ext in sorted(all_extensions))
        return f"All supported files ({ext_string})"

    def is_dicom_folder(self, folder_path: Path) -> bool:
        """
        Check if a folder contains DICOM files.

        Args:
            folder_path: Path to the folder to check

        Returns:
            True if folder contains DICOM files, False otherwise
        """
        folder_path = Path(folder_path)
        if not folder_path.is_dir():
            return False

        # Common DICOM extensions
        dicom_extensions = {'.dcm', '.DCM', '.dicom', '.DICOM', '.ima', '.IMA'}

        # Check for DICOM files
        file_count = 0
        dicom_count = 0

        for file_path in folder_path.iterdir():
            if file_path.is_file():
                file_count += 1

                # Check extension
                if file_path.suffix in dicom_extensions:
                    dicom_count += 1

                # Check files without extensions (common in DICOM)
                elif not file_path.suffix and file_count < 20:  # Sample first 20 files
                    # Could add DICOM header detection here if needed
                    pass

                # Stop early if clearly DICOM folder
                if dicom_count >= 3:
                    return True

        # Consider it DICOM if significant portion are DICOM files
        return dicom_count > 0 and (dicom_count / max(file_count, 1)) > 0.1

    def get_conversion_options(self, file_path: Path) -> list[dict[str, str]]:
        """
        Get all available conversion options for a file.

        Args:
            file_path: Path to source file

        Returns:
            List of conversion option dictionaries
        """
        converters = self.converter_registry.get_all_converters(Path(file_path))

        options = []
        for converter in converters:
            options.append({
                'converter_name': converter.__class__.__name__,
                'target_format': converter.target_format,
                'description': converter.description,
                'priority': str(converter.priority)
            })

        return options

    def validate_file_for_datatype(self, file_path: Path, datatype: str) -> tuple[bool, list[str]]:
        """
        Validate if a file is appropriate for a specific BIDS datatype.

        Args:
            file_path: Path to the file
            datatype: Target BIDS datatype

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        modality_info = self.get_modality_info(datatype)
        if not modality_info:
            errors.append(f"Unknown datatype: {datatype}")
            return False, errors

        # Check if file extension is compatible (either directly or via conversion)
        extension = file_path.suffix.lower()
        filename = file_path.name.lower()

        # Handle compound extensions
        full_extension = extension
        if filename.endswith('.nii.gz'):
            full_extension = '.nii.gz'

        # Check direct compatibility
        if extension in modality_info.extensions or full_extension in modality_info.extensions:
            return True, []

        # Check conversion compatibility
        converter = self.converter_registry.get_converter(file_path)
        if converter:
            # Check if converter output is compatible with datatype
            target_extensions = self.schema_manager.file_registry.get_supported_extensions(datatype)
            converter_target_format = converter.target_format

            if converter_target_format in target_extensions:
                return True, []
            else:
                errors.append(f"Converter output format {converter_target_format} not compatible with {datatype}")
        else:
            errors.append(f"File extension {extension} not compatible with {datatype} and no converter available")

        return len(errors) == 0, errors
