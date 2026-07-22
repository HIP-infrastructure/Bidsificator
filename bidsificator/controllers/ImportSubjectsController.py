"""Controller for batch subject import operations."""

import logging
import tempfile
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from ..core.BidsSubjectSchema import BidsSubject
from ..core.BidsUtilityFunctions import BidsUtilityFunctions
from ..core.schema import BidsSchemaManager
from ..models.SubjectDataModel import SubjectData, SubjectDataModel
from ..services.SubjectLookupService import SubjectLookupService
from ..workers.BidsSubjectsProcess import check_subject_conflicts
from ..workers.import_processor import SKIPPED, ImportItemOutcome
from ..workers.ImportBidsSubjectsWorker import ImportBidsSubjectsWorker

logger = logging.getLogger(__name__)


class ImportSubjectsController(QObject):
    """Controller for coordinating batch subject import operations."""

    # Signals for UI updates
    progress_updated = pyqtSignal(int)  # Progress value 0-100
    import_completed = pyqtSignal(dict)  # Import results
    import_failed = pyqtSignal(str)  # Error message
    subjects_loaded = pyqtSignal()  # Subject list updated
    selection_changed = pyqtSignal(int)  # Selected subject index changed
    file_list_updated = pyqtSignal()  # File list for selected subject updated
    lookup_table_updated = pyqtSignal(str)  # Lookup table status message
    required_entities_changed = pyqtSignal(dict)  # Required entities for UI updated
    dialog_dismissed = pyqtSignal()  # Completion dialog was closed by user
    operation_failed = pyqtSignal(str, str)  # (title, message) warning for the view
    operation_info = pyqtSignal(str, str)  # (title, message) information for the view

    def __init__(self, dataset_path_provider, file_editor_controller, parent: QWidget | None = None):
        """
        Initialize import subjects controller.

        Args:
            dataset_path_provider: Callable that returns current dataset path
            file_editor_controller: Controller for file editor operations
            parent: Parent widget for dialogs (optional)
        """
        super().__init__()
        self._parent_widget = parent
        self._get_dataset_path = dataset_path_provider
        self._file_editor_controller = file_editor_controller
        self._model = SubjectDataModel()
        self._worker: ImportBidsSubjectsWorker | None = None
        # Subjects the user chose to skip at the conflict dialog. They are filtered
        # out before the worker starts, so they never reach the subprocess summary;
        # the controller merges them back in on completion (REQ-GUI-073).
        self._skipped_existing: list[str] = []
        self._config_path = BidsUtilityFunctions.get_config_path()
        self._lookup_table_path: str | None = None
        self._subject_mapping: dict[str, str] = {}
        self._schema_manager = BidsSchemaManager.get_instance()

    @property
    def model(self) -> SubjectDataModel:
        """Get the subject data model."""
        return self._model

    @property
    def subject_count(self) -> int:
        """Get number of subjects."""
        return self._model.count()

    @property
    def selected_subject_index(self) -> int:
        """Get currently selected subject index."""
        return self._model.selected_subject_index

    @selected_subject_index.setter
    def selected_subject_index(self, index: int):
        """Set currently selected subject index."""
        self._model.selected_subject_index = index
        self.selection_changed.emit(index)
        self._update_file_editor()

    def parse_subjects_to_import(self, config_path: str | None = None) -> bool:
        """
        Parse subjects from configuration file.

        Args:
            config_path: Path to configuration file (optional, uses default if None)

        Returns:
            True if subjects were parsed successfully
        """
        if config_path:
            self._config_path = config_path

        try:
            # Use model to crawl and load subjects with subject mapping
            self._model.crawl_and_load_subjects(self._config_path, self._subject_mapping)

            # Emit signal for UI update
            self.subjects_loaded.emit()

            # Emit required entities for dynamic UI
            required_entities = self.get_required_entities_for_import()
            self.required_entities_changed.emit(required_entities)

            # Update file editor with first subject if available
            if self._model.count() > 0:
                self.selected_subject_index = 0

            return True

        except Exception as e:
            error_message = f"Failed to parse subjects: {str(e)}"
            self.operation_failed.emit("Parse Failed", error_message)
            self.import_failed.emit(error_message)
            return False

    def get_subject_ids(self) -> list[str]:
        """
        Get list of subject IDs.

        Returns:
            List of subject ID strings
        """
        return self._model.get_subject_ids()

    def get_display_names(self) -> list[str]:
        """
        Get list of display names for UI (original [mapped] format).

        Returns:
            List of display name strings
        """
        return self._model.get_display_names()

    def get_selected_subject(self) -> SubjectData | None:
        """
        Get currently selected subject.

        Returns:
            SubjectData instance or None if no selection
        """
        return self._model.get_selected_subject()

    def remove_selected_subjects(self, selected_indices: list[int]) -> bool:
        """
        Remove multiple selected subjects.

        The view gathers the confirmation before calling this.

        Args:
            selected_indices: List of indices to remove

        Returns:
            True if any subjects were removed
        """
        if not selected_indices:
            return False

        # Remove subjects (in descending order to avoid index issues)
        removed_count = self._model.remove_selected_subjects(sorted(selected_indices, reverse=True))

        if removed_count > 0:
            # Update UI
            self.subjects_loaded.emit()

            # Clear file editor
            self._file_editor_controller.clear_file_list()

            return True

        return False

    def start_batch_import(
        self,
        task: str = "Rest",
        conflict_resolver: Callable[[list[str]], str] | None = None,
    ) -> bool:
        """
        Start the batch import process.

        Args:
            task: BIDS task entity value to apply to all imported files
            conflict_resolver: Called with the list of conflicting subject IDs
                when the dataset already contains some of them; must return
                "overwrite", "skip", or "cancel". The view supplies this (it owns
                the conflict dialog). When omitted, a conflict cancels the import.

        Returns:
            True if started successfully
        """
        # Reset per-run state so a prior run's skips don't leak into this summary.
        self._skipped_existing = []

        dataset_path = self._get_dataset_path()
        if not dataset_path:
            self.operation_failed.emit("No Dataset", "Please load a dataset first")
            return False

        if self._model.is_empty():
            self.operation_failed.emit("No Subjects", "Please parse subjects first")
            return False

        # Check if a worker is already running
        if self._worker and self._worker.isRunning():
            self.operation_failed.emit("Import in Progress", "An import is already in progress")
            return False

        # Validate all subjects before import
        all_valid, errors = self._model.validate_all_subjects()
        if not all_valid:
            error_message = "Validation errors found:\n" + "\n".join(errors)
            self.operation_failed.emit("Validation Failed", error_message)
            return False

        # Prepare subjects for import
        subjects_data = self._model.prepare_for_import()
        if not subjects_data:
            self.operation_failed.emit("No Valid Subjects", "No valid subjects found for import")
            return False

        # Check for subject conflicts before starting import
        try:
            existing_subjects = check_subject_conflicts(dataset_path, subjects_data)
            overwrite_existing = False

            if existing_subjects:
                # The view resolves the conflict (overwrite / skip / cancel).
                conflict_result = conflict_resolver(existing_subjects) if conflict_resolver else "cancel"

                if conflict_result == "cancel":
                    return False  # User cancelled
                elif conflict_result == "overwrite":
                    overwrite_existing = True
                elif conflict_result == "skip":
                    overwrite_existing = False
                    # Remember the skips so they appear in the completion summary,
                    # then filter out the conflicting subjects before the worker.
                    self._skipped_existing = list(existing_subjects)
                    subjects_data = [s for s in subjects_data
                                   if f"sub-{s['subject_id']}" not in existing_subjects]

                    if not subjects_data:
                        self.operation_info.emit(
                            "No Subjects to Import",
                            "All subjects already exist and were skipped.",
                        )
                        return False

        except Exception as e:
            self.operation_failed.emit(
                "Error Checking Conflicts",
                f"Failed to check for existing subjects: {str(e)}",
            )
            return False

        # Create and start worker with overwrite setting and task
        self._worker = ImportBidsSubjectsWorker(dataset_path, subjects_data, overwrite_existing, task)
        self._worker.update_progressbar_signal.connect(self._on_progress_updated)
        self._worker.import_finished.connect(self._on_import_finished)
        self._worker.error.connect(self._on_import_error)
        self._worker.start()

        return True

    def _on_progress_updated(self, progress: int):
        """Handle progress update from worker."""
        self.progress_updated.emit(progress)

    def _on_import_finished(self, summary):
        """Handle import completion from worker.

        Counts come from the worker's ``ImportSummary`` (what was actually created
        and placed), not the queued model counts. Subjects the user skipped at the
        conflict dialog were filtered out before the worker, so they are merged
        back into the summary here as skipped items (REQ-GUI-073). The ``summary``
        sub-dict feeds the ticket-3 completion dialog; the flat ``subjects_imported``
        / ``total_files`` keys keep the current dialog working meanwhile.
        """
        for existing in self._skipped_existing:
            summary.items.append(ImportItemOutcome(
                path=None, subject=existing, status=SKIPPED,
                reason="Subject already exists (user chose skip)",
            ))

        results = {
            "subjects_imported": summary.subjects_created,
            "total_files": summary.imported,
            "summary": summary.to_dict(),
        }

        self.import_completed.emit(results)

        # Clean up worker
        if self._worker:
            self._worker.deleteLater()
            self._worker = None

        # The view clears the status bar on dialog_dismissed. Emit it only for a
        # clean success; on a partial import the view shows a persistent amber
        # "finished with N problems" message that must survive the dialog closing,
        # so we deliberately withhold dialog_dismissed (mirrors the error path).
        # summary.skipped already includes the merged conflict-dialog skips above.
        if summary.failed == 0 and summary.skipped == 0 and not summary.warnings:
            self.dialog_dismissed.emit()

    def _on_import_error(self, message: str):
        """Handle import failure from worker (child crash or reported error)."""
        # Clean up worker
        if self._worker:
            self._worker.deleteLater()
            self._worker = None

        # Notify the view, which shows the status-bar error and the modal.
        # Deliberately do NOT emit dialog_dismissed here so the error stays in
        # the status bar.
        self.import_failed.emit(message)

    def _update_file_editor(self):
        """Update file editor with currently selected subject."""
        selected_subject = self._model.get_selected_subject()

        if selected_subject:
            # Convert subject data to legacy format for file editor
            legacy_subject = {
                "subject_id": selected_subject.subject_id,
                "files": selected_subject.files
            }

            # Update file editor
            self._file_editor_controller.add_files_to_list(legacy_subject)
        else:
            # Clear file editor if no selection
            self._file_editor_controller.clear_file_list()

        self.file_list_updated.emit()

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about subjects and files.

        Returns:
            Dictionary with statistics
        """
        return self._model.get_statistics()

    def clear_subjects(self):
        """Clear all subjects from the model."""
        self._model.clear()
        self.subjects_loaded.emit()
        self._file_editor_controller.clear_file_list()
        self.file_list_updated.emit()

    def is_import_in_progress(self) -> bool:
        """Check if import is currently in progress."""
        return self._worker is not None and self._worker.isRunning()

    def get_subject_by_id(self, subject_id: str) -> SubjectData | None:
        """
        Get subject by ID.

        Args:
            subject_id: Subject ID to find

        Returns:
            SubjectData instance or None if not found
        """
        return self._model.get_subject_by_id(subject_id)

    def get_required_entities_for_import(self) -> dict[str, list[str]]:
        """
        Analyze imported files and determine which entities are required.

        Returns:
            Dictionary mapping entity keys to their possible values from schema
        """
        if self._model.is_empty():
            return {}

        # Collect all unique datatype/suffix combinations from imported files
        datatype_suffix_pairs = set()

        for subject_data in self._model.subjects:
            for file_info in subject_data.files:
                modality = file_info.get('modality', '')

                # Schema-driven modality parsing
                # Format: "T1w (anat)" or "ieeg (ieeg)" or just "ieeg"
                if '(' in modality and ')' in modality:
                    # Extract suffix and datatype: "T1w (anat)" -> suffix="T1w", datatype="anat"
                    suffix = modality.split('(')[0].strip()
                    datatype = modality.split('(')[1].split(')')[0].strip()
                else:
                    # Format without parentheses - use as both suffix and datatype
                    suffix = modality.strip()
                    datatype = modality.strip()

                # Validate datatype exists in schema
                if datatype in self._schema_manager.datatypes:
                    dt = self._schema_manager.get_datatype(datatype)
                    # Validate suffix is valid for this datatype
                    if suffix in dt.suffixes or datatype == suffix:
                        datatype_suffix_pairs.add((datatype, suffix))
                    else:
                        logger.warning("Suffix '%s' not valid for datatype '%s' - skipping", suffix, datatype)
                else:
                    logger.warning("Unknown datatype '%s' from modality '%s' - skipping", datatype, modality)

        # Collect all required entities across all file types
        # Use existing proven schema logic from BidsSubject (same as Tab 2)
        all_required_entities = set()

        # Create a temporary BidsSubject to use its proven schema methods
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_subject = BidsSubject('temp', temp_dir, self._schema_manager)

            for datatype, suffix in datatype_suffix_pairs:
                required = temp_subject.get_required_entities_for_suffix(datatype, suffix)
                all_required_entities.update(required)

        # Build entity requirements with possible values
        entity_requirements = {}
        for entity in all_required_entities:
            if entity == 'task':
                # For task entity, we could query schema for allowed values
                # For now, provide common iEEG task values
                entity_requirements['task'] = ['Cognitiv', 'Seizure', 'Interictal', 'Stimulation', 'Sleep', 'Rest']
            elif entity == 'ses':
                entity_requirements['ses'] = ['pre', 'post', 'intra', '01', '02']
            # Add more entities as needed

        return entity_requirements

    def set_config_path(self, config_path: str):
        """
        Set the configuration file path for data crawling.

        Args:
            config_path: Path to configuration file
        """
        self._config_path = config_path


    def update_subject_data(self, subject_id: str, modified_data: dict[str, Any]) -> bool:
        """
        Update a subject's data with modified data from FileEditor.

        Args:
            subject_id: Subject ID to update
            modified_data: Modified subject data dictionary

        Returns:
            True if updated successfully
        """
        # Find the subject in our model
        for _i, subject in enumerate(self._model.subjects):
            if subject.subject_id == subject_id:
                # Update the subject's files with the modified data
                subject.files = modified_data.get("files", [])
                return True

        return False

    def _reapply_mapping_to_loaded_subjects(self):
        """Re-map already-parsed subjects to the current mapping and refresh the UI.

        No-op when no subjects are loaded yet (the mapping is then applied at the
        next Parse). Preserves per-subject file edits (re-maps in place, no crawl).
        """
        if self._model.count() > 0:
            self._model.reapply_subject_mapping(self._subject_mapping)
            self.subjects_loaded.emit()

    def set_lookup_table(self, csv_path: str) -> bool:
        """
        Set the lookup table for subject name mapping.

        Args:
            csv_path: Path to CSV lookup table file

        Returns:
            True if successful, False if validation failed
        """
        if not csv_path:
            # Clear lookup table
            self._lookup_table_path = None
            self._subject_mapping = {}
            # Revert any already-parsed subjects to their original names.
            self._reapply_mapping_to_loaded_subjects()
            self.lookup_table_updated.emit("Lookup table cleared")
            return True

        # Validate CSV format first
        is_valid, format_errors = SubjectLookupService.validate_csv_format(csv_path)
        if not is_valid:
            error_message = "CSV validation failed:\n" + "\n".join(format_errors)
            self.operation_failed.emit("Invalid Lookup Table", error_message)
            self.lookup_table_updated.emit("Invalid lookup table format")
            return False

        # Parse the CSV file
        mapping, parse_errors = SubjectLookupService.parse_lookup_table(csv_path)

        if parse_errors:
            error_message = "CSV parsing failed:\n" + "\n".join(parse_errors[:10])  # Limit errors shown
            if len(parse_errors) > 10:
                error_message += f"\n... and {len(parse_errors) - 10} more errors"

            self.operation_failed.emit("Lookup Table Parsing Error", error_message)
            self.lookup_table_updated.emit(f"Parsing failed: {len(parse_errors)} errors")
            return False

        # Successfully parsed
        self._lookup_table_path = csv_path
        self._subject_mapping = mapping

        # Apply the mapping to any subjects already parsed, so the anonymization
        # takes effect regardless of whether the lookup table was loaded before
        # or after Parse (it is applied at crawl time too, in parse_subjects_to_import).
        self._reapply_mapping_to_loaded_subjects()

        status_message = f"Loaded {len(mapping)} subject mappings"
        self.lookup_table_updated.emit(status_message)

        # Show success message with preview
        preview_list = list(mapping.items())[:5]  # Show first 5 mappings
        preview_text = "\n".join([f"{orig} → {mapped}" for orig, mapped in preview_list])
        if len(mapping) > 5:
            preview_text += f"\n... and {len(mapping) - 5} more"

        self.operation_info.emit(
            "Lookup Table Loaded",
            f"Successfully loaded {len(mapping)} subject mappings.\n\nPreview:\n{preview_text}",
        )

        return True

    def get_lookup_table_path(self) -> str | None:
        """Get current lookup table path."""
        return self._lookup_table_path

    def has_lookup_table(self) -> bool:
        """Check if lookup table is loaded."""
        return bool(self._lookup_table_path and self._subject_mapping)

    def get_mapping_count(self) -> int:
        """Get number of mappings in lookup table."""
        return len(self._subject_mapping)

    def get_mapping_preview(self, limit: int = 10) -> list[tuple[str, str]]:
        """
        Get preview of current mappings.

        Args:
            limit: Maximum number of mappings to return

        Returns:
            List of (original_id, mapped_name) tuples
        """
        return list(self._subject_mapping.items())[:limit]

    def save_lookup_template(self, file_path: str) -> tuple[bool, str]:
        """
        Create a lookup-table template at ``file_path``.

        The save dialog now lives in the view; this writes the template
        (pre-populated with the parsed subject IDs when available) and returns
        ``(success, message)`` so the view can show the outcome.

        Args:
            file_path: Destination chosen by the user (``.csv`` is appended if missing).

        Returns:
            Tuple of (success, message) — ``message`` is the success text or the error.
        """
        # Ensure .csv extension
        if not file_path.lower().endswith('.csv'):
            file_path += '.csv'

        # Get current subject IDs for pre-population (if available)
        current_subject_ids = self.get_subject_ids() if self._model.count() > 0 else None

        success, error_message = SubjectLookupService.create_template_file(file_path, current_subject_ids)

        if success:
            subject_count = len(current_subject_ids) if current_subject_ids else 3
            if current_subject_ids:
                message = (
                    f"Template created successfully with {subject_count} pre-populated subject IDs.\n\n"
                    f"File saved to:\n{file_path}\n\n"
                    f"Please fill in the CenterName and NumericID columns."
                )
            else:
                message = (
                    f"Template created successfully with example entries.\n\n"
                    f"File saved to:\n{file_path}\n\n"
                    f"Please replace the example data with your actual anonymous subject information."
                )

            # Update the lookup table path field to point to the new template
            self.lookup_table_updated.emit(f"Template created: {subject_count} entries")
            return True, message

        self.lookup_table_updated.emit("Template creation failed")
        return False, f"Failed to create template file:\n\n{error_message}"
