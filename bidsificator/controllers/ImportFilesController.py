"""Controller for single file import tab operations."""

import logging
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from ..models.ImportSessionModel import ImportSessionModel
from ..workers.ImportBidsFilesWorker import ImportBidsFilesWorker

logger = logging.getLogger(__name__)


class ImportFilesController(QObject):
    """Controller for coordinating single file import operations."""

    # Signals for UI updates
    progress_updated = pyqtSignal(int)  # Progress value 0-100
    import_completed = pyqtSignal(dict)  # Import results
    import_failed = pyqtSignal(str)  # Error message
    file_list_changed = pyqtSignal()  # File list updated
    selection_changed = pyqtSignal(int)  # Selected file index changed
    form_data_updated = pyqtSignal(dict)  # Form data for selected file
    dialog_dismissed = pyqtSignal()  # Completion dialog was closed by user
    operation_failed = pyqtSignal(str, str)  # (title, message) for the view to render

    def __init__(self, dataset_path_provider, parent: QWidget | None = None):
        """
        Initialize import files controller.

        Args:
            dataset_path_provider: Callable that returns current dataset path
            parent: Parent widget for dialogs (optional)
        """
        super().__init__()
        self._parent_widget = parent
        self._get_dataset_path = dataset_path_provider
        self._model = ImportSessionModel()
        self._worker: ImportBidsFilesWorker | None = None
        self._contact_labeling_file: str | None = None

        # Set up default configuration
        self._model.config.auto_detect_modality = True
        self._model.config.auto_increment_acquisition = True

    @property
    def model(self) -> ImportSessionModel:
        """Get the import session model."""
        return self._model

    @property
    def current_subject(self) -> str:
        """Get current subject ID."""
        return self._model.file_model.current_subject

    @current_subject.setter
    def current_subject(self, subject_id: str):
        """Set current subject ID."""
        self._model.file_model.current_subject = subject_id

    @property
    def file_count(self) -> int:
        """Get number of files in import list."""
        return self._model.file_model.count()

    @property
    def contact_labeling_file(self) -> str | None:
        """Get the optional contact-labeling Excel file for the current session."""
        return self._contact_labeling_file

    @contact_labeling_file.setter
    def contact_labeling_file(self, path: str | None):
        """Set (or clear) the contact-labeling Excel file for the current session."""
        self._contact_labeling_file = path

    @property
    def selected_file_index(self) -> int:
        """Get currently selected file index."""
        return self._model.selected_file_index

    @selected_file_index.setter
    def selected_file_index(self, index: int):
        """Set currently selected file index."""
        self._model.selected_file_index = index
        self.selection_changed.emit(index)

        # Emit form data for selected file
        form_data = self._model.get_form_data_for_selected_file()
        if form_data:
            self.form_data_updated.emit(form_data)

    def add_files_from_paths(self, files: list[str], form_defaults: dict[str, str]) -> tuple[int, list[str]]:
        """
        Add the given files to the import session.

        The file-selection dialog now lives in the view; this method takes the
        chosen paths, adds them to the model, and returns the outcome so the view
        can show the results summary.

        Args:
            files: Paths chosen by the user (empty is a no-op).
            form_defaults: Default form values to apply to files.

        Returns:
            Tuple of (successful_count, failed_files).
        """
        if not files:
            return 0, []

        # Add files to the model
        successful_count, failed_files = self._model.add_files(files, form_defaults)

        # Emit signals for UI updates
        self.file_list_changed.emit()

        if successful_count > 0 and self._model.selected_file_index == -1:
            self.selected_file_index = 0

        return successful_count, failed_files

    def remove_selected_file(self) -> bool:
        """
        Remove currently selected file from import list.

        Returns:
            True if removed successfully
        """
        if self._model.selected_file_index == -1:
            self.operation_failed.emit("No Selection", "Please select a file to remove")
            return False

        success = self._model.remove_selected_file()
        if success:
            self.file_list_changed.emit()

            # Update selection
            if self._model.file_model.count() > 0:
                self.selection_changed.emit(self._model.selected_file_index)
            else:
                self.selection_changed.emit(-1)

        return success

    def update_selected_file_from_form(self, form_data: dict[str, str]) -> bool:
        """
        Update selected file with form data.

        Args:
            form_data: Dictionary with form field values

        Returns:
            True if updated successfully
        """
        return self._model.update_selected_file_from_form(form_data)

    def update_files_from_form(self, indices: list[int], fields: dict[str, str]) -> bool:
        """Batch-apply ``fields`` to the files at ``indices`` (multi-select edit).

        Delegates to the model, which writes only the given fields and reassigns
        acquisition for files whose group key changed. Deliberately does **not**
        emit ``file_list_changed``: the list shows file names, which a metadata
        edit never changes, so a rebuild would only collapse the user's
        multi-selection. The view refreshes its own batch form after this returns.

        Args:
            indices: File indices to update.
            fields: Form field values to apply (subset of the form keys).

        Returns:
            True if at least one file was updated.
        """
        return self._model.update_files_from_form(indices, fields)

    def needs_subject_change_confirmation(self, new_subject: str) -> bool:
        """
        Whether switching to ``new_subject`` should prompt the user first.

        True only when files are already queued and the subject actually changes
        — the case where the view asks "apply to all queued files?" before
        calling :meth:`change_subject`.
        """
        current_subject = self._model.file_model.current_subject
        return (not self._model.file_model.is_empty()) and current_subject != new_subject

    def change_subject(self, new_subject: str) -> bool:
        """
        Change subject for all files in the session.

        The confirmation prompt (when files are queued) now lives in the view —
        see :meth:`needs_subject_change_confirmation`; this just applies the change.

        Args:
            new_subject: New subject ID

        Returns:
            True if changed successfully
        """
        return self._model.change_subject(new_subject)

    def _check_electrodes_will_be_overwritten(self, dataset_path: str, subject_id: str) -> bool:
        """
        Check if electrodes.tsv exists for this subject.

        Args:
            dataset_path: Path to BIDS dataset
            subject_id: Subject identifier

        Returns:
            True if electrodes.tsv exists and will be overwritten
        """
        from pathlib import Path

        try:
            subject_path = Path(dataset_path) / f"sub-{subject_id}"

            # Check if subject folder exists
            if not subject_path.exists():
                return False

            # Check all possible locations for electrodes.tsv
            # Could be in multiple session folders or directly in subject
            electrodes_files = list(subject_path.glob("**/sub-*_electrodes.tsv"))

            return len(electrodes_files) > 0

        except Exception:
            logger.warning("Could not check for existing electrodes.tsv", exc_info=True)
            return False

    def import_would_regenerate_electrodes(self) -> bool:
        """
        Whether starting the import would overwrite an existing electrodes.tsv.

        True only when a contact-labeling file is set AND the current subject
        already has an electrodes.tsv under the loaded dataset — the case the
        view confirms before calling :meth:`start_import`.
        """
        dataset_path = self._get_dataset_path()
        if not dataset_path or not self._contact_labeling_file:
            return False
        subject_name = self._model.get_legacy_data_structure()["subject_id"]
        return self._check_electrodes_will_be_overwritten(dataset_path, subject_name)

    def start_import(self) -> bool:
        """
        Start the import process.

        The electrodes.tsv-regeneration confirmation (when a contact-labeling
        file is set) is gathered by the view beforehand — see
        :meth:`import_would_regenerate_electrodes`.

        Returns:
            True if started successfully
        """
        dataset_path = self._get_dataset_path()
        if not dataset_path:
            self.operation_failed.emit("No Dataset", "Please load a dataset first")
            return False

        if not self._model.start_import():
            self.operation_failed.emit("Import Failed", self._model.error_message or "Cannot start import")
            return False

        # Check if a worker is already running
        if self._worker and self._worker.isRunning():
            self.operation_failed.emit("Import in Progress", "An import is already in progress")
            return False

        # Prepare data for worker
        legacy_data = self._model.get_legacy_data_structure()
        subject_name = legacy_data["subject_id"]
        files = legacy_data["files"]

        # Create and start worker with optional contact labeling file
        self._worker = ImportBidsFilesWorker(
            dataset_path,
            subject_name,
            files,
            self._contact_labeling_file
        )
        self._worker.update_progressbar_signal.connect(self._on_progress_updated)
        self._worker.import_finished.connect(self._on_import_finished)
        self._worker.error.connect(self._on_import_error)
        self._worker.start()

        return True

    def _on_progress_updated(self, progress: int):
        """Handle progress update from worker."""
        self._model.progress = progress
        self.progress_updated.emit(progress)

    def _on_import_finished(self, summary):
        """Handle import completion from worker.

        Counts come from the worker's ``ImportSummary`` (what actually landed on
        disk), not the queued ``file_count``. The ``summary`` sub-dict carries the
        per-item outcomes and warnings for the completion dialog (consumed by the
        ticket-3 UI); the flat ``files_imported`` key keeps the current dialog
        working in the meantime.
        """
        results = {
            "files_imported": summary.imported,
            "subject": self.current_subject,
            "summary": summary.to_dict(),
        }

        self._model.complete_import(results)
        self.import_completed.emit(results)

        # Clean up worker
        if self._worker:
            self._worker.deleteLater()
            self._worker = None

        # The view clears the status bar on dialog_dismissed. Emit it only for a
        # clean success; on a partial import the view shows a persistent amber
        # "finished with N problems" message that must survive the dialog closing,
        # so we deliberately withhold dialog_dismissed (mirrors the error path).
        if summary.failed == 0 and summary.skipped == 0 and not summary.warnings:
            self.dialog_dismissed.emit()

    def _on_import_error(self, message: str):
        """Handle import failure from worker (child crash or reported error)."""
        # Clean up worker
        if self._worker:
            self._worker.deleteLater()
            self._worker = None

        # Reset the session out of IMPORTING so a subsequent import is allowed;
        # without this the model stays IMPORTING and start_import refuses every
        # retry ("Cannot start import").
        self._model.fail_import(message)

        # Notify the view, which shows the status-bar error and the modal.
        # Deliberately do NOT emit dialog_dismissed here so the error stays in
        # the status bar.
        self.import_failed.emit(message)

    def clear_session(self):
        """Clear the current import session."""
        self._model.reset_session()
        self.file_list_changed.emit()
        self.selection_changed.emit(-1)

    def get_session_summary(self) -> dict[str, Any]:
        """
        Get summary of current session.

        Returns:
            Dictionary with session information
        """
        return self._model.get_session_summary()

    def get_file_names_for_list_widget(self) -> list[str]:
        """
        Get file names for display in list widget.

        Returns:
            List of file names for display
        """
        files = self._model.file_model.get_files_as_dicts()
        return [file_data["file_name"] for file_data in files]

    def is_import_in_progress(self) -> bool:
        """Check if import is currently in progress."""
        return self._worker is not None and self._worker.isRunning()
