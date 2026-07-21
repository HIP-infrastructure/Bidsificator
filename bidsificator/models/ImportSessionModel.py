"""Model for managing import session state and operations."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .ImportFileModel import ImportFileData, ImportFileModel


class ImportSessionState(Enum):
    """States for import session."""
    IDLE = "idle"
    IMPORTING = "importing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ImportSessionConfig:
    """Configuration for import session."""
    auto_detect_modality: bool = True
    auto_increment_acquisition: bool = True
    allow_duplicate_files: bool = False
    validate_files: bool = True


class ImportSessionModel:
    """Model for managing import session state and operations."""

    def __init__(self):
        """Initialize import session model."""
        self._file_model = ImportFileModel()
        self._state = ImportSessionState.IDLE
        self._config = ImportSessionConfig()
        self._selected_file_index = -1
        self._progress = 0
        self._error_message = ""
        self._import_results: dict[str, Any] = {}

    @property
    def file_model(self) -> ImportFileModel:
        """Get the file model."""
        return self._file_model

    @property
    def state(self) -> ImportSessionState:
        """Get current session state."""
        return self._state

    @state.setter
    def state(self, new_state: ImportSessionState):
        """Set session state."""
        self._state = new_state
        if new_state == ImportSessionState.IDLE:
            self._progress = 0
            self._error_message = ""

    @property
    def config(self) -> ImportSessionConfig:
        """Get session configuration."""
        return self._config

    @property
    def selected_file_index(self) -> int:
        """Get currently selected file index."""
        return self._selected_file_index

    @selected_file_index.setter
    def selected_file_index(self, index: int):
        """Set currently selected file index."""
        if -1 <= index < self._file_model.count():
            self._selected_file_index = index
        else:
            self._selected_file_index = -1

    @property
    def progress(self) -> int:
        """Get import progress (0-100)."""
        return self._progress

    @progress.setter
    def progress(self, value: int):
        """Set import progress."""
        self._progress = max(0, min(100, value))

    @property
    def error_message(self) -> str:
        """Get error message."""
        return self._error_message

    @error_message.setter
    def error_message(self, message: str):
        """Set error message."""
        self._error_message = message
        if message:
            self._state = ImportSessionState.ERROR

    @property
    def import_results(self) -> dict[str, Any]:
        """Get import results."""
        return self._import_results.copy()

    def get_selected_file(self) -> ImportFileData | None:
        """
        Get currently selected file data.

        Returns:
            ImportFileData instance or None if no selection
        """
        return self._file_model.get_file(self._selected_file_index)

    def update_selected_file(self, file_data: ImportFileData) -> bool:
        """
        Update currently selected file data.

        Args:
            file_data: New file data

        Returns:
            True if updated successfully
        """
        if self._selected_file_index >= 0:
            return self._file_model.update_file(self._selected_file_index, file_data)
        return False

    def add_files(self, file_paths: list[str], form_defaults: dict[str, str]) -> tuple[int, list[str]]:
        """
        Add multiple files to the session.

        Args:
            file_paths: List of file paths to add
            form_defaults: Default form values to apply

        Returns:
            Tuple of (successful_count, failed_files)
        """
        from ..services.ImportService import ImportService

        # Use ImportService to process the files
        successful_files, failed_files = ImportService.process_multiple_files(
            file_paths,
            form_defaults,
            self._file_model.get_files_as_dicts()
        )

        # Add successful files to the model
        added_count = 0
        for file_dict in successful_files:
            file_data = ImportFileData.from_dict(file_dict)
            if self._file_model.add_file(file_data):
                added_count += 1

        # Update selection to first file if this is the first addition
        if self._file_model.count() == added_count and added_count > 0:
            self.selected_file_index = 0

        return added_count, failed_files

    def remove_selected_file(self) -> bool:
        """
        Remove currently selected file.

        Returns:
            True if removed successfully
        """
        if self._selected_file_index >= 0:
            if self._file_model.remove_file(self._selected_file_index):
                # Update selection after removal
                total_files = self._file_model.count()
                if total_files == 0:
                    self.selected_file_index = -1
                elif self._selected_file_index >= total_files:
                    self.selected_file_index = total_files - 1
                return True
        return False

    def change_subject(self, new_subject: str) -> bool:
        """
        Change subject for all files in session.

        Args:
            new_subject: New subject ID

        Returns:
            True if changed successfully
        """
        if not new_subject:
            return False

        self._file_model.update_all_subjects(new_subject)
        return True

    def start_import(self) -> bool:
        """
        Start the import process.

        Returns:
            True if started successfully
        """
        if self._state == ImportSessionState.IMPORTING:
            return False

        if self._file_model.is_empty():
            self._error_message = "No files to import"
            self._state = ImportSessionState.ERROR
            return False

        # Validate files if configured
        if self._config.validate_files:
            all_valid, errors = self._file_model.validate_all()
            if not all_valid:
                self._error_message = "Validation errors: " + "; ".join(errors)
                self._state = ImportSessionState.ERROR
                return False

        self._state = ImportSessionState.IMPORTING
        self._progress = 0
        self._error_message = ""
        return True

    def complete_import(self, results: dict[str, Any]):
        """
        Mark import as completed.

        Args:
            results: Import results dictionary
        """
        self._import_results = results
        self._state = ImportSessionState.COMPLETED
        self._progress = 100

    def reset_session(self):
        """Reset the session to initial state."""
        self._file_model.clear()
        self._state = ImportSessionState.IDLE
        self._selected_file_index = -1
        self._progress = 0
        self._error_message = ""
        self._import_results = {}

    def get_session_summary(self) -> dict[str, Any]:
        """
        Get summary of current session.

        Returns:
            Dictionary with session information
        """
        stats = self._file_model.get_statistics()

        return {
            "state": self._state.value,
            "file_count": self._file_model.count(),
            "current_subject": self._file_model.current_subject,
            "selected_file_index": self._selected_file_index,
            "progress": self._progress,
            "has_error": bool(self._error_message),
            "error_message": self._error_message,
            "file_statistics": stats,
            "import_results": self._import_results
        }

    def can_modify_files(self) -> bool:
        """
        Check if files can be modified in current state.

        Returns:
            True if files can be modified
        """
        return self._state in [ImportSessionState.IDLE, ImportSessionState.COMPLETED, ImportSessionState.ERROR]

    def get_form_data_for_selected_file(self) -> dict[str, str] | None:
        """
        Get form data for currently selected file.

        Returns:
            Dictionary with form field values or None if no selection
        """
        file_data = self.get_selected_file()
        if not file_data:
            return None

        return {
            "file_path": file_data.file_path,
            "modality": file_data.modality,
            "session": file_data.get_session_with_prefix(),
            "task": file_data.task,
            "contrast_agent": file_data.contrast_agent,
            "acquisition": file_data.acquisition,
            "reconstruction": file_data.reconstruction
        }

    def update_selected_file_from_form(self, form_data: dict[str, str]) -> bool:
        """
        Update selected file from form data.

        Args:
            form_data: Dictionary with form field values

        Returns:
            True if updated successfully
        """
        file_data = self.get_selected_file()
        if not file_data:
            return False

        # Update the file data
        file_data.modality = form_data.get("modality", file_data.modality)
        file_data.task = form_data.get("task", file_data.task)
        file_data.contrast_agent = form_data.get("contrast_agent", file_data.contrast_agent)
        file_data.acquisition = form_data.get("acquisition", file_data.acquisition)
        file_data.reconstruction = form_data.get("reconstruction", file_data.reconstruction)

        # Handle session (remove ses- prefix if present)
        session = form_data.get("session", file_data.session)
        if session.startswith("ses-"):
            session = session[4:]
        file_data.session = session

        return self.update_selected_file(file_data)

    # Backward compatibility methods

    def get_legacy_data_structure(self) -> dict[str, Any]:
        """
        Get data in legacy format for backward compatibility.

        Returns:
            Dictionary matching original MainWindow format
        """
        return {
            "subject_id": self._file_model.current_subject,
            "files": self._file_model.get_files_as_dicts()
        }
