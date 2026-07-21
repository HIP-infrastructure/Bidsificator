"""Controller for dataset creation, loading, and management operations."""


from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from ..models.DatasetModel import DatasetModel
from ..services.ValidationServiceSchema import ValidationService


class DatasetController(QObject):
    """Controller for coordinating dataset operations between model and UI.

    This controller is UI-free: gathering user input (folder, dataset name) and
    rendering dialogs are the view's responsibility. Feedback that used to be
    shown here via ``QMessageBox`` / the validation dialogs is now emitted as
    signals the view connects to those dialogs, so the controller no longer
    imports anything from ``..ui`` (the previously inverted dependency).
    """

    # Feedback signals — the view connects these to dialogs.
    operation_failed = pyqtSignal(str, str)   # (title, message) for an error/warning box
    validation_started = pyqtSignal(str)      # status message for the progress dialog
    validation_finished = pyqtSignal(object)  # ValidationResult for the results dialog

    def __init__(self, parent_widget: QWidget | None = None):
        """
        Initialize dataset controller.

        Args:
            parent_widget: Retained for API compatibility; dialogs now live in
                the view, so this is no longer used to parent them.
        """
        super().__init__()
        self._parent_widget = parent_widget
        self._model = DatasetModel()

    @property
    def model(self) -> DatasetModel:
        """Get the dataset model."""
        return self._model

    @property
    def is_dataset_loaded(self) -> bool:
        """Check if a dataset is currently loaded."""
        return self._model.is_loaded

    @property
    def dataset_path(self) -> str:
        """Get current dataset path."""
        return self._model.dataset_path

    @property
    def dataset_name(self) -> str:
        """Get current dataset name."""
        return self._model.dataset_name

    @property
    def subjects(self) -> list[str]:
        """Get list of subjects in current dataset."""
        return self._model.subjects

    def create_new_dataset(self, folder_path: str, dataset_name: str) -> tuple[bool, str]:
        """
        Create a new BIDS dataset from view-supplied inputs.

        Args:
            folder_path: Folder chosen by the user to hold the dataset
            dataset_name: Name entered by the user

        Returns:
            Tuple of (success, dataset_path or error_message)
        """
        if not folder_path:
            return False, "No folder selected"

        if not dataset_name or not dataset_name.strip():
            self.operation_failed.emit("Dataset Name empty", "Please enter a dataset name")
            return False, "Empty dataset name"

        # Create the dataset using the model
        success, error_message = self._model.create_dataset(folder_path, dataset_name)

        if success:
            return True, self._model.dataset_path

        self.operation_failed.emit("Dataset Creation Failed", error_message)
        return False, error_message

    def load_existing_dataset(self, folder_path: str) -> tuple[bool, str]:
        """
        Load an existing BIDS dataset from a view-supplied folder.

        Args:
            folder_path: Folder chosen by the user

        Returns:
            Tuple of (success, dataset_path or error_message)
        """
        if not folder_path:
            return False, "No folder selected"

        # Load the dataset using the model
        success, error_message = self._model.load_dataset(folder_path)

        if success:
            return True, self._model.dataset_path

        self.operation_failed.emit("Dataset Loading Failed", error_message)
        return False, error_message

    def load_dataset_from_path(self, dataset_path: str) -> tuple[bool, str]:
        """
        Load a dataset from a specific path.

        Args:
            dataset_path: Path to the dataset

        Returns:
            Tuple of (success, error_message)
        """
        return self._model.load_dataset(dataset_path)

    def create_subject(self, subject_name: str) -> tuple[bool, str]:
        """
        Create a new subject in the current dataset.

        Args:
            subject_name: Name of the subject to create

        Returns:
            Tuple of (success, error_message)
        """
        if not self._model.is_loaded:
            error = "No dataset loaded"
            self.operation_failed.emit("No dataset selected", "Please open a BIDS dataset first")
            return False, error

        if not subject_name:
            error = "Subject name cannot be empty"
            self.operation_failed.emit("Subject Name empty", "Please enter a subject name")
            return False, error

        if not subject_name.startswith("sub-"):
            error = "Subject name should start with 'sub-'"
            self.operation_failed.emit("Subject Name not valid", error)
            return False, error

        # Use model to add the subject
        success, error_message = self._model.add_subject(subject_name)

        if not success:
            self.operation_failed.emit("Subject Creation Failed", error_message)

        return success, error_message

    def validate_dataset(self, subject_name: str | None = None) -> tuple[bool, str]:
        """
        Validate the current dataset or a specific subject.

        Emits ``validation_started`` (so the view can show a progress dialog)
        and ``validation_finished`` with the result (so the view can show the
        results dialog). On error, emits ``operation_failed`` instead.

        Args:
            subject_name: Optional subject to validate specifically

        Returns:
            Tuple of (is_valid, message)
        """
        if not self._model.is_loaded:
            error = "No dataset loaded"
            self.operation_failed.emit("No Dataset found", "Please load a Dataset first")
            return False, error

        # Announce start so the view can open a progress dialog.
        if subject_name:
            self.validation_started.emit(f"Validating subject {subject_name}...")
        else:
            self.validation_started.emit("Validating entire dataset...")

        try:
            validation_service = ValidationService()
            dataset_path = self._model.current_dataset.path

            if subject_name:
                # Subject-specific validation (no dataset-level checks)
                validation_result = validation_service.validate_subject(dataset_path, subject_name)
            else:
                # Full dataset validation (includes dataset-level checks)
                validation_result = validation_service.validate_dataset(dataset_path)

            # Hand the result to the view for the results dialog.
            self.validation_finished.emit(validation_result)

            return validation_result.is_valid, validation_result.message

        except Exception as e:
            self.operation_failed.emit(
                "Validation Error", f"An error occurred during validation: {str(e)}"
            )
            return False, str(e)

    def delete_files(self, file_paths: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
        """
        Delete files from disk via the model.

        Args:
            file_paths: Absolute paths of the files to delete

        Returns:
            Tuple of (deleted_paths, failed) where ``failed`` is a list of
            ``(path, reason)`` tuples.
        """
        return self._model.delete_files(file_paths)

    def get_sessions_for_subject(self, subject_id: str) -> list[str]:
        """
        Get sessions for a specific subject.

        Args:
            subject_id: Subject ID to get sessions for

        Returns:
            List of session names
        """
        return self._model.get_sessions_for_subject(subject_id)

    def refresh_subjects(self):
        """Refresh the subjects list from filesystem."""
        self._model.refresh_subjects()

    def get_dataset_statistics(self) -> dict:
        """
        Get comprehensive dataset statistics.

        Returns:
            Dictionary with dataset statistics
        """
        return self._model.get_dataset_statistics()

    def close_dataset(self):
        """Close the current dataset."""
        self._model.close_dataset()

    def get_tree_model_path(self) -> str | None:
        """
        Get dataset path for tree view model.

        Returns:
            Dataset path or None if no dataset loaded
        """
        return self._model.get_tree_model_data()
