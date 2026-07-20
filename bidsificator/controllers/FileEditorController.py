"""Controller for file editor operations."""

from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QWidget

from ..services.ValidationServiceSchema import ValidationService


class FileEditorController(QObject):
    """Controller for coordinating file editor operations."""

    # Signals for UI updates
    file_list_updated = pyqtSignal()  # File list changed
    file_selected = pyqtSignal(dict)  # File data for selected file
    task_list_updated = pyqtSignal(list)  # Task list changed
    edit_mode_changed = pyqtSignal(bool)  # Edit mode enabled/disabled

    def __init__(self, parent: QWidget | None = None):
        """
        Initialize file editor controller.

        Args:
            parent: Parent widget for dialogs (optional)
        """
        super().__init__()
        self._parent_widget = parent
        self._current_subject_data: dict[str, Any] | None = None
        self._selected_file_index = -1
        self._edit_mode = False
        self._file_memory: dict[str, str] | None = None

        # Keep track of available tasks for dynamic task management
        self._available_tasks: list[str] = []

    @property
    def has_files(self) -> bool:
        """Check if there are files loaded."""
        return (self._current_subject_data is not None and
                len(self._current_subject_data.get("files", [])) > 0)

    @property
    def selected_file_index(self) -> int:
        """Get currently selected file index."""
        return self._selected_file_index

    @property
    def edit_mode(self) -> bool:
        """Check if edit mode is enabled."""
        return self._edit_mode

    def add_files_to_list(self, subject_data: dict[str, Any]):
        """
        Add files to the editor list.

        Args:
            subject_data: Subject data with files list
        """
        self._current_subject_data = subject_data
        self._selected_file_index = -1

        # Emit signal for UI update
        self.file_list_updated.emit()

        # Auto-select first file if available
        if self.has_files:
            self.select_file(0)

    def append_to_list(self, subject_data: dict[str, Any]) -> str:
        """
        Append a single file to the existing list.

        Args:
            subject_data: Subject data with single file

        Returns:
            Empty string on success, error message on failure
        """
        if not self._current_subject_data:
            # No existing data, treat as new list
            self.add_files_to_list(subject_data)
            return ""

        new_subject_id = subject_data.get("subject_id", "")
        current_subject_id = self._current_subject_data.get("subject_id", "")
        new_file = subject_data.get("files", [{}])[0] if subject_data.get("files") else {}

        # Check for subject ID mismatch
        if new_subject_id != current_subject_id:
            self.clear_file_list()
            self._current_subject_data = subject_data
            self.file_list_updated.emit()
            if self.has_files:
                self.select_file(0)
            return "Subject ID mismatch, all previous files were removed"

        # Check for duplicate file
        current_files = self._current_subject_data.get("files", [])
        for existing_file in current_files:
            if existing_file.get("file_path") == new_file.get("file_path"):
                return "File already exists"

        # Add the new file
        current_files.append(new_file)
        self.file_list_updated.emit()
        return ""

    def save_current_form_data(self, form_data: dict[str, str]) -> bool:
        """
        Save form data to currently selected file.

        Args:
            form_data: Dictionary with form field values

        Returns:
            True if saved successfully
        """
        if (self._selected_file_index < 0 or
            not self._current_subject_data or
            self._selected_file_index >= len(self._current_subject_data.get("files", []))):
            return False

        # Update the selected file with form data
        file_data = self._current_subject_data["files"][self._selected_file_index]

        # Save all form fields to the file data
        file_data["modality"] = form_data.get("modality", "")
        file_data["session"] = form_data.get("session", "").removeprefix("ses-")
        file_data["task"] = form_data.get("task", "")
        file_data["contrast_agent"] = form_data.get("contrast_agent", "")
        file_data["acquisition"] = form_data.get("acquisition", "")
        file_data["reconstruction"] = form_data.get("reconstruction", "")

        return True

    def remove_selected_file(self) -> bool:
        """
        Remove currently selected file.

        Returns:
            True if removed successfully
        """
        if not self.has_files or self._selected_file_index < 0:
            return False

        files = self._current_subject_data["files"]
        if 0 <= self._selected_file_index < len(files):
            files.pop(self._selected_file_index)

            # Update selection
            if len(files) == 0:
                self._selected_file_index = -1
            elif self._selected_file_index >= len(files):
                self._selected_file_index = len(files) - 1

            # Update UI
            self.file_list_updated.emit()
            if self._selected_file_index >= 0:
                self.select_file(self._selected_file_index)

            return True

        return False

    def select_file(self, index: int):
        """
        Select a file by index.

        Args:
            index: Index of file to select
        """
        if not self.has_files:
            self._selected_file_index = -1
            return

        files = self._current_subject_data["files"]
        if 0 <= index < len(files):
            self._selected_file_index = index
            file_data = files[index]

            # Store file data in memory for edit operations
            self._file_memory = file_data.copy()

            # Emit file data for UI update
            self.file_selected.emit(file_data)
        else:
            self._selected_file_index = -1

    def get_selected_file_data(self) -> dict[str, str] | None:
        """
        Get data for currently selected file.

        Returns:
            File data dictionary or None if no selection
        """
        if not self.has_files or self._selected_file_index < 0:
            return None

        files = self._current_subject_data["files"]
        if 0 <= self._selected_file_index < len(files):
            return files[self._selected_file_index].copy()

        return None

    def update_selected_file(self, field_data: dict[str, str]) -> bool:
        """
        Update selected file with new field data.

        Args:
            field_data: Dictionary with field names and values

        Returns:
            True if updated successfully
        """
        if not self.has_files or self._selected_file_index < 0:
            return False

        files = self._current_subject_data["files"]
        if 0 <= self._selected_file_index < len(files):
            file_data = files[self._selected_file_index]

            # Update fields
            for field_name, value in field_data.items():
                if field_name in file_data:
                    file_data[field_name] = value

            return True

        return False

    def toggle_edit_mode(self) -> bool:
        """
        Toggle edit mode on/off. When exiting edit mode, save changes.

        Returns:
            New edit mode state
        """
        if self._edit_mode:
            # Exiting edit mode - save changes
            self.save_edit_changes()

        self._edit_mode = not self._edit_mode
        self.edit_mode_changed.emit(self._edit_mode)
        return self._edit_mode

    def enable_edit_mode(self):
        """Enable edit mode."""
        if not self._edit_mode:
            self._edit_mode = True
            self.edit_mode_changed.emit(True)

    def disable_edit_mode(self):
        """Disable edit mode."""
        if self._edit_mode:
            self._edit_mode = False
            self.edit_mode_changed.emit(False)

    def cancel_edit_changes(self):
        """Cancel edit changes and restore from memory."""
        if self._file_memory and self.has_files and self._selected_file_index >= 0:
            files = self._current_subject_data["files"]
            if 0 <= self._selected_file_index < len(files):
                # Restore from memory
                files[self._selected_file_index] = self._file_memory.copy()

                # Emit updated file data
                self.file_selected.emit(self._file_memory.copy())

                # Exit edit mode
                self._edit_mode = False
                self.edit_mode_changed.emit(False)

    def save_edit_changes(self):
        """Save current edit changes to memory."""
        if self.has_files and self._selected_file_index >= 0:
            files = self._current_subject_data["files"]
            if 0 <= self._selected_file_index < len(files):
                # Update memory with current file state
                self._file_memory = files[self._selected_file_index].copy()

    def handle_task_selection(self, task_name: str, current_tasks: list[str]) -> tuple[str, list[str]]:
        """
        Handle task selection, including "Other" option.

        Args:
            task_name: Selected task name
            current_tasks: Current list of available tasks

        Returns:
            Tuple of (final_task_name, updated_task_list)
        """
        if "Other" not in task_name:
            return task_name, current_tasks

        # Handle "Other" selection
        new_task, ok = QInputDialog.getText(
            self._parent_widget,
            "Enter Task Name",
            "Enter a name for your task"
        )

        if not ok or not new_task.strip():
            if not new_task.strip():
                QMessageBox.warning(
                    self._parent_widget,
                    "Task Name empty",
                    "Please enter a valid name for your task"
                )
            return "", current_tasks  # Return empty to indicate cancellation

        # Validate task name
        validation_service = ValidationService()
        is_valid, error = validation_service.validate_task_name(new_task)
        if not is_valid:
            QMessageBox.warning(
                self._parent_widget,
                "Invalid Task Name",
                error
            )
            return "", current_tasks

        # Add new task to the list (insert before "Other")
        updated_tasks = current_tasks.copy()
        if "Other" in updated_tasks:
            other_index = updated_tasks.index("Other")
            updated_tasks.insert(other_index, new_task)
        else:
            updated_tasks.append(new_task)

        # Update available tasks and emit signal
        self._available_tasks = updated_tasks
        self.task_list_updated.emit(updated_tasks)

        return new_task, updated_tasks

    def get_file_names_for_list(self) -> list[str]:
        """
        Get file names for display in list widget.

        Returns:
            List of file names
        """
        if not self.has_files:
            return []

        files = self._current_subject_data["files"]
        return [file_data.get("file_name", "Unknown") for file_data in files]

    def clear_file_list(self):
        """Clear all files from the list."""
        self._current_subject_data = None
        self._selected_file_index = -1
        self._edit_mode = False
        self._file_memory = None

        # Emit signals for UI update
        self.file_list_updated.emit()
        self.edit_mode_changed.emit(False)

    def get_file_count(self) -> int:
        """Get number of files in the list."""
        if not self.has_files:
            return 0
        return len(self._current_subject_data["files"])

    def get_current_subject_id(self) -> str:
        """Get current subject ID."""
        if self._current_subject_data:
            return self._current_subject_data.get("subject_id", "")
        return ""

    def validate_selected_file(self) -> tuple[bool, str]:
        """
        Validate currently selected file.

        Returns:
            Tuple of (is_valid, error_message)
        """
        file_data = self.get_selected_file_data()
        if not file_data:
            return False, "No file selected"

        # Check required fields
        if not file_data.get("file_path"):
            return False, "File path is required"

        if not file_data.get("modality"):
            return False, "Modality is required"

        # Validate file exists
        import os
        if not os.path.exists(file_data["file_path"]):
            return False, f"File does not exist: {file_data['file_path']}"

        # Validate BIDS naming components if present
        validation_service = ValidationService()

        session = file_data.get("session", "")
        if session:
            is_valid, error = validation_service.validate_session_name(session)
            if not is_valid:
                return False, f"Invalid session: {error}"

        task = file_data.get("task", "")
        if task:
            is_valid, error = validation_service.validate_task_name(task)
            if not is_valid:
                return False, f"Invalid task: {error}"

        acquisition = file_data.get("acquisition", "")
        if acquisition:
            is_valid, error = validation_service.validate_acquisition_name(acquisition)
            if not is_valid:
                return False, f"Invalid acquisition: {error}"

        return True, ""

    def get_modality_ui_requirements(self, modality: str) -> dict[str, bool]:
        """
        Get UI requirements for a specific modality.

        Args:
            modality: Datatype string (e.g., "ieeg", "anat")

        Returns:
            Dictionary with UI element visibility requirements
        """
        from ..services.FileDetectionServiceSchema import FileDetectionService

        detection_service = FileDetectionService()
        modality_info = detection_service.get_modality_info(modality)

        if modality_info:
            return modality_info.ui_requirements
        else:
            # Default requirements if modality not found
            return {
                'show_session': True,
                'show_task': False,
                'show_contrast': False,
                'show_acquisition': True,
                'show_reconstruction': False,
                'show_direction': False,
                'show_run': True
            }

