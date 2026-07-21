"""Main controller coordinating all main window operations."""

from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from .DatasetController import DatasetController
from .FileEditorController import FileEditorController
from .ImportFilesController import ImportFilesController
from .ImportSubjectsController import ImportSubjectsController
from .OptionController import OptionController


class MainController(QObject):
    """Main controller coordinating all application operations."""

    # Signals for high-level UI updates
    dataset_changed = pyqtSignal(str)  # Dataset path changed
    subjects_updated = pyqtSignal()  # Subject list needs refresh
    progress_updated = pyqtSignal(int)  # Overall progress update
    status_updated = pyqtSignal(str)  # Status message update

    def __init__(self, parent_widget: QWidget | None = None):
        """
        Initialize main controller.

        Args:
            parent_widget: Parent widget for child controllers
        """
        super().__init__()
        self._parent_widget = parent_widget

        # Initialize all sub-controllers
        self._dataset_controller = DatasetController(parent_widget)
        self._file_editor_controller = FileEditorController(parent_widget)
        self._import_files_controller = ImportFilesController(
            self._get_dataset_path, parent_widget
        )
        self._import_subjects_controller = ImportSubjectsController(
            self._get_dataset_path, self._file_editor_controller, parent_widget
        )
        self._option_controller = OptionController()

        # Connect inter-controller signals
        self._setup_controller_connections()

    def _setup_controller_connections(self):
        """Set up connections between controllers."""
        # Dataset changes trigger subject list updates
        self._dataset_controller.model.dataset_changed = self.dataset_changed

        # Import completion triggers subject list refresh
        self._import_files_controller.import_completed.connect(self._on_import_completed)
        self._import_subjects_controller.import_completed.connect(self._on_import_completed)

        # Progress forwarding
        self._import_files_controller.progress_updated.connect(self.progress_updated)
        self._import_subjects_controller.progress_updated.connect(self.progress_updated)

    def _get_dataset_path(self) -> str:
        """Get current dataset path for child controllers."""
        return self._dataset_controller.dataset_path

    def _on_import_completed(self, results: dict[str, Any]):
        """Handle import completion from any controller."""
        # Refresh subjects from filesystem first
        self._dataset_controller.refresh_subjects()
        self.subjects_updated.emit()
        self.status_updated.emit("Import completed successfully")

    # Dataset operations

    @property
    def dataset_controller(self) -> DatasetController:
        """Get dataset controller."""
        return self._dataset_controller

    def create_dataset(self, folder_path: str, dataset_name: str):
        """
        Create a new dataset from view-supplied inputs.

        Args:
            folder_path: Folder chosen by the user to hold the dataset
            dataset_name: Name entered by the user
        """
        success, result = self._dataset_controller.create_new_dataset(folder_path, dataset_name)
        if success:
            self.dataset_changed.emit(result)
            self.subjects_updated.emit()
            self.status_updated.emit(f"Dataset created: {self._dataset_controller.dataset_name}")

    def open_dataset(self, folder_path: str):
        """
        Open an existing dataset from a view-supplied folder.

        Args:
            folder_path: Folder chosen by the user
        """
        success, result = self._dataset_controller.load_existing_dataset(folder_path)
        if success:
            self.dataset_changed.emit(result)
            self.subjects_updated.emit()
            self.status_updated.emit(f"Dataset loaded: {self._dataset_controller.dataset_name}")

    def delete_dataset_files(self, file_paths: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
        """
        Delete files from disk through the dataset controller.

        Args:
            file_paths: Absolute paths of the files to delete

        Returns:
            Tuple of (deleted_paths, failed) where ``failed`` is a list of
            ``(path, reason)`` tuples.
        """
        return self._dataset_controller.delete_files(file_paths)

    def create_subject(self, subject_name: str):
        """
        Create a new subject in the current dataset.

        Args:
            subject_name: Name of subject to create
        """
        success, error = self._dataset_controller.create_subject(subject_name)
        if success:
            self.subjects_updated.emit()
            self.status_updated.emit(f"Subject created: {subject_name}")

    def validate_bids_dataset(self, subject_name: str | None = None):
        """
        Validate the BIDS dataset.

        Args:
            subject_name: Optional specific subject to validate
        """
        is_valid, message = self._dataset_controller.validate_dataset(subject_name)
        if subject_name:
            status = f"Subject {subject_name}: {'Valid' if is_valid else 'Invalid'}"
        else:
            status = f"Dataset: {'Valid' if is_valid else 'Invalid'}"
        self.status_updated.emit(status)

    # Import Files operations

    @property
    def import_files_controller(self) -> ImportFilesController:
        """Get import files controller."""
        return self._import_files_controller

    def start_file_import(self):
        """Start single file import process."""
        success = self._import_files_controller.start_import()
        if success:
            self.status_updated.emit("File import started...")

    # Import Subjects operations

    @property
    def import_subjects_controller(self) -> ImportSubjectsController:
        """Get import subjects controller."""
        return self._import_subjects_controller

    def parse_subjects_to_import(self, config_path: str | None = None):
        """
        Parse subjects from configuration.

        Args:
            config_path: Optional configuration file path
        """
        success = self._import_subjects_controller.parse_subjects_to_import(config_path)
        if success:
            count = self._import_subjects_controller.subject_count
            self.status_updated.emit(f"Parsed {count} subjects for import")

    def remove_selected_import_subjects(self, selected_indices: list[int]):
        """
        Remove selected subjects from import list.

        Args:
            selected_indices: List of indices to remove
        """
        success = self._import_subjects_controller.remove_selected_subjects(selected_indices)
        if success:
            self.status_updated.emit("Selected subjects removed")

    def start_subjects_import(self, task: str = "Rest", conflict_resolver=None):
        """Start batch subjects import process.

        ``conflict_resolver`` is forwarded to the controller; the view supplies it
        to resolve subject conflicts (overwrite / skip / cancel).
        """
        success = self._import_subjects_controller.start_batch_import(task, conflict_resolver)
        if success:
            self.status_updated.emit("Batch import started...")

    # File Editor operations

    @property
    def file_editor_controller(self) -> FileEditorController:
        """Get file editor controller."""
        return self._file_editor_controller

    # Options operations

    @property
    def option_controller(self) -> OptionController:
        """Get option controller."""
        return self._option_controller

    def open_options_window(self):
        """Open options/configuration window."""
        # This will be handled by the UI layer, but controller is available
        self.status_updated.emit("Opening options...")

    # Utility methods

    def get_current_subjects(self) -> list[str]:
        """Get list of subjects in current dataset."""
        return self._dataset_controller.subjects

    def get_sessions_for_subject(self, subject_id: str) -> list[str]:
        """
        Get sessions for a subject.

        Args:
            subject_id: Subject ID

        Returns:
            List of session names
        """
        return self._dataset_controller.get_sessions_for_subject(subject_id)

    def refresh_subjects(self):
        """Refresh subject list from filesystem."""
        self._dataset_controller.refresh_subjects()
        self.subjects_updated.emit()

    def is_dataset_loaded(self) -> bool:
        """Check if a dataset is currently loaded."""
        return self._dataset_controller.is_dataset_loaded

    def get_dataset_tree_path(self) -> str | None:
        """Get dataset path for tree view."""
        return self._dataset_controller.get_tree_model_path()

    def is_any_import_in_progress(self) -> bool:
        """Check if any import operation is in progress."""
        return (self._import_files_controller.is_import_in_progress() or
                self._import_subjects_controller.is_import_in_progress())

    def get_application_status(self) -> dict[str, Any]:
        """
        Get comprehensive application status.

        Returns:
            Dictionary with application state information
        """
        return {
            "dataset_loaded": self.is_dataset_loaded(),
            "dataset_name": self._dataset_controller.dataset_name,
            "dataset_path": self._dataset_controller.dataset_path,
            "subject_count": len(self._dataset_controller.subjects),
            "import_files_count": self._import_files_controller.file_count,
            "import_subjects_count": self._import_subjects_controller.subject_count,
            "any_import_in_progress": self.is_any_import_in_progress(),
            "file_editor_has_files": self._file_editor_controller.has_files
        }

