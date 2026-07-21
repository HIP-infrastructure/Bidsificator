"""
Improved schema-driven BidsSubject implementation

Improvements over BidsSubjectNew:
- No inline classes
- Extracted constants to bids_constants module
- Proper file analysis abstraction
- Cleaner code structure
- Better separation of concerns

`BidsSubject` models a subject directory: its identity, optional metadata, and
directory/file listing. The heavy file-writing work is delegated to two
collaborators created in ``__init__``:
- `SubjectFileWriter` — the ``add_file`` pipeline (analysis, conversion, entity
  validation, path construction, copying the data file).
- `SubjectSidecarGenerator` — JSON sidecars and companion TSV/JSON files.
The thin ``add_file`` / ``analyze_file`` / ``_build_*`` / ``_generate_*`` /
``_create_*`` methods below delegate to those collaborators, preserving the
historical public and ``_``-prefixed surface that callers and tests rely on.
"""

import logging
from pathlib import Path
from typing import Any

from bidsificator.converters.registry import ConverterRegistry
from bidsificator.core.bids_constants import BIDS_DATA_EXTENSIONS
from bidsificator.core.filename_builder import FilenameBuilder
from bidsificator.core.schema import BidsSchemaManager
from bidsificator.core.subject_file_writer import SubjectFileWriter
from bidsificator.core.subject_sidecar_generator import SubjectSidecarGenerator

logger = logging.getLogger(__name__)


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
            logger.debug("Sanitized subject ID: '%s' → '%s'", subject_id, sanitized_subject_id)

        if not self.schema.validate_entity_value('sub', sanitized_subject_id):
            raise ValueError(f"Invalid subject ID '{sanitized_subject_id}' according to BIDS schema")

        # Use sanitized ID
        self.subject_id = sanitized_subject_id

        self.subject_path = self._build_subject_path()
        self.subject_path.mkdir(parents=True, exist_ok=True)

        # Initialize converter registry
        self.converter_registry = ConverterRegistry()

        # Initialize filename builder
        self.filename_builder = FilenameBuilder()

        # Track optional metadata for this subject
        self.optional_metadata: dict[str, Any] = {}

        # Track contact labeling file for SEEG subjects
        self.contact_labeling_file: Path | None = None

        # File-writing collaborators. Each holds a back-reference to this
        # subject and reads its live state, so a rename or optional-metadata
        # update is always reflected.
        self._file_writer = SubjectFileWriter(self)
        self._sidecar_generator = SubjectSidecarGenerator(self)

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
            logger.warning("Key not found: %s", key)

    def set_contact_labeling_file(self, file_path: Path | None):
        """
        Set the contact labeling file for this subject

        Args:
            file_path: Path to Excel file with contact labeling data, or None to clear
        """
        if file_path is not None:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Contact labeling file not found: {file_path}")
            if file_path.suffix.lower() not in ['.xlsx', '.xls']:
                raise ValueError(f"Contact labeling file must be Excel format (.xlsx or .xls): {file_path}")
        self.contact_labeling_file = file_path

    def get_contact_labeling_file(self) -> Path | None:
        """
        Get the contact labeling file for this subject

        Returns:
            Path to contact labeling file, or None if not set
        """
        return self.contact_labeling_file

    def has_contact_labeling_file(self) -> bool:
        """
        Check if this subject has a contact labeling file

        Returns:
            True if contact labeling file is set and exists
        """
        return (self.contact_labeling_file is not None and
                self.contact_labeling_file.exists())

    def _build_subject_path(self) -> Path:
        """Build subject directory path"""
        return self.dataset_path / self._format_entity('sub', self.subject_id)


    def _format_entity(self, entity_key: str, entity_value: str) -> str:
        """Format entity with prefix (e.g., 'sub-01')"""
        return f"{entity_key}-{entity_value}"

    def get_subject_path(self) -> Path:
        """Get full subject directory path"""
        return self.subject_path

    def set_optional_metadata(self, metadata: dict[str, Any]):
        """Set optional metadata that will be included in all files"""
        self.optional_metadata.update(metadata)

    def get_datatype_path(self, datatype: str, session: str | None = None) -> Path:
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

    # ------------------------------------------------------------------
    # File-writing delegation
    #
    # These thin methods forward to the `SubjectFileWriter` /
    # `SubjectSidecarGenerator` collaborators. They preserve the public and
    # historical ``_``-prefixed surface reached by callers (api, workers,
    # controllers) and the existing tests. Cross-collaborator calls also route
    # through these same methods, so the subject stays the single mediator.
    # ------------------------------------------------------------------

    def add_file(self,
                 source_path: Path,
                 datatype: str,
                 entities: dict[str, str] | None = None,
                 suffix: str | None = None,
                 metadata: dict[str, Any] | None = None,
                 target_format: str | None = None) -> dict[str, Any]:
        """Add a file to the subject (delegates to SubjectFileWriter)."""
        return self._file_writer.add_file(
            source_path, datatype, entities=entities, suffix=suffix,
            metadata=metadata, target_format=target_format,
        )

    def analyze_file(self, source_path: Path, target_format: str | None = None):
        """Analyze a file for BIDS processing (delegates to SubjectFileWriter)."""
        return self._file_writer.analyze_file(source_path, target_format)

    def get_required_entities_for_suffix(self, datatype: str, suffix: str) -> list[str]:
        """Get required entity keys for a datatype/suffix (delegates to SubjectFileWriter)."""
        return self._file_writer.get_required_entities_for_suffix(datatype, suffix)

    def _build_bids_filename(self, entities: dict[str, str], suffix: str, extension: str) -> str:
        """Build a BIDS-compliant filename (delegates to SubjectFileWriter)."""
        return self._file_writer._build_bids_filename(entities, suffix, extension)

    def _build_target_path(self, entities: dict[str, str], datatype: str,
                           suffix: str, extension: str) -> Path:
        """Build a BIDS-compliant target path (delegates to SubjectFileWriter)."""
        return self._file_writer._build_target_path(entities, datatype, suffix, extension)

    def _generate_metadata_files(self, data_path: Path, datatype: str, suffix: str,
                                 entities: dict[str, str], user_metadata: dict[str, Any],
                                 source_path: Path = None):
        """Generate JSON sidecar + companion files (delegates to SubjectSidecarGenerator)."""
        return self._sidecar_generator._generate_metadata_files(
            data_path, datatype, suffix, entities, user_metadata, source_path,
        )

    def _generate_ephys_files(self, data_path: Path, entities: dict[str, str],
                              datatype: str, source_path: Path = None):
        """Generate electrophysiology companion files (delegates to SubjectSidecarGenerator)."""
        return self._sidecar_generator._generate_ephys_files(
            data_path, entities, datatype, source_path,
        )

    def _get_default_metadata_value(self, field_name: str, field_spec: dict[str, Any],
                                    entities: dict[str, str], datatype: str = None,
                                    suffix: str = None) -> Any:
        """Get a default metadata value (delegates to SubjectSidecarGenerator)."""
        return self._sidecar_generator._get_default_metadata_value(
            field_name, field_spec, entities, datatype, suffix,
        )

    def _create_channels_dataframe(self, datatype: str, channel_count: int):
        """Create a channels dataframe (delegates to SubjectSidecarGenerator)."""
        return self._sidecar_generator._create_channels_dataframe(datatype, channel_count)

    def _create_events_dataframe(self):
        """Create an empty events dataframe (delegates to SubjectSidecarGenerator)."""
        return self._sidecar_generator._create_events_dataframe()

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

    def list_files(self, datatype: str | None = None,
                  session: str | None = None) -> list[Path]:
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

    def get_sessions(self) -> list[str]:
        """Get list of sessions for this subject"""
        sessions = []
        for item in self.subject_path.iterdir():
            if item.is_dir() and item.name.startswith('ses-'):
                sessions.append(item.name.replace('ses-', ''))
        return sorted(sessions)

    def get_datatypes(self, session: str | None = None) -> list[str]:
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
        This method updates the subject ID and renames the subject folder and all files
        recursively with the new subject ID.

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
                    for root, _dirs, files in os.walk(old_subject_path):
                        for file in files:
                            if old_folder_name in file:
                                old_file_path = os.path.join(root, file)
                                new_file_name = file.replace(old_folder_name, new_folder_name)
                                new_file_path = os.path.join(root, new_file_name)
                                try:
                                    os.rename(old_file_path, new_file_path)
                                except OSError:
                                    logger.exception("Error renaming file %s to %s", old_file_path, new_file_path)
                                    raise

                    # Rename the subject folder itself
                    try:
                        os.rename(str(old_subject_path), str(new_subject_path))
                    except OSError:
                        logger.exception("Error renaming folder %s to %s", old_subject_path, new_subject_path)
                        raise

                    # Update the internal state
                    self.subject_id = new_subject_id
                    self.subject_path = new_subject_path
                else:
                    logger.warning("Subject path does not exist: %s", old_subject_path)
            except Exception:
                logger.exception("Error in set_subject_id")
                raise
