"""Controller for patient/subject table operations."""

import logging
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QWidget

from ..core.BidsFolder import BidsFolder
from ..services.ValidationServiceSchema import ValidationService

logger = logging.getLogger(__name__)


class PatientTableController(QObject):
    """Controller for coordinating patient/subject table operations."""

    # Signals for UI updates
    subjects_loaded = pyqtSignal()  # Subject list updated
    subject_created = pyqtSignal(str)  # New subject created
    subject_updated = pyqtSignal(str)  # Subject data updated
    subject_deleted = pyqtSignal(str)  # Subject deleted
    keys_updated = pyqtSignal()  # Table columns/keys updated
    data_changed = pyqtSignal()  # Table data changed

    def __init__(self, dataset_path_provider, parent: QWidget | None = None):
        """
        Initialize patient table controller.

        Args:
            dataset_path_provider: Callable that returns current dataset path
            parent: Parent widget for dialogs (optional)
        """
        super().__init__()
        self._parent_widget = parent
        self._get_dataset_path = dataset_path_provider
        self._bids_folder: BidsFolder | None = None
        self._subjects_data: list[dict[str, Any]] = []
        self._all_optional_keys: dict[str, str] = {}
        self._selected_subject: str | None = None

    def load_subjects(self, dataset_path: str) -> bool:
        """
        Load subjects from dataset.

        Args:
            dataset_path: Path to the dataset

        Returns:
            True if loaded successfully
        """
        try:
            self._bids_folder = BidsFolder(dataset_path)
            bids_subjects = self._bids_folder.get_bids_subjects()

            # Convert to internal format
            self._subjects_data = []
            all_optional_keys = {}

            for subject in bids_subjects:
                subject_dict = {
                    "subject_id": subject.get_subject_id(),
                    **subject.get_optional_keys()
                }
                self._subjects_data.append(subject_dict)

                # Collect all unique optional keys
                for key in subject.get_optional_keys().keys():
                    all_optional_keys[key] = self._get_default_value_for_key(key)

            self._all_optional_keys = all_optional_keys

            # Emit signals for UI update
            self.subjects_loaded.emit()
            self.keys_updated.emit()

            return True

        except Exception:
            logger.exception("Error loading subjects")
            self._subjects_data = []
            self._all_optional_keys = {}
            return False

    def _get_default_value_for_key(self, key: str) -> str:
        """Get default value for a subject key."""
        default_values = {
            'age': '25',
            'sex': 'M'
        }
        return default_values.get(key.lower(), "n/a")

    def _sync_data_from_bids_folder(self):
        """Sync internal data model from current BidsFolder."""
        if not self._bids_folder:
            return

        bids_subjects = self._bids_folder.get_bids_subjects()

        # Convert to internal format
        self._subjects_data = []
        all_optional_keys = {}

        for subject in bids_subjects:
            subject_dict = {
                "subject_id": subject.get_subject_id(),
                **subject.get_optional_keys()
            }
            self._subjects_data.append(subject_dict)

            # Collect all unique optional keys
            for key in subject.get_optional_keys().keys():
                all_optional_keys[key] = self._get_default_value_for_key(key)

        self._all_optional_keys = all_optional_keys

        # Emit signals for UI update
        self.subjects_loaded.emit()
        self.keys_updated.emit()

    def create_subject(self, subject_id: str) -> tuple[bool, str]:
        """
        Create a new subject in the dataset.

        Args:
            subject_id: Subject ID to create

        Returns:
            Tuple of (success, error_message)
        """
        if not self._bids_folder:
            return False, "No dataset loaded"

        # Strip "sub-" prefix if provided (case-insensitive) to prevent double prefix
        if subject_id.lower().startswith("sub-"):
            subject_id = subject_id[4:]

        # Validate subject ID
        validation_service = ValidationService()
        is_valid, error = validation_service.validate_subject_name(subject_id)
        if not is_valid:
            return False, error

        try:
            # Get subject description from current keys
            subject_description = self._all_optional_keys.copy()
            if not subject_description:
                subject_description = {'age': 25, 'sex': 'M'}

            # Actually create the subject in the BIDS dataset
            self._bids_folder.add_bids_subject(subject_id, subject_description)

            # Generate/update the participants.tsv file
            self._bids_folder.generate_participants_tsv()

            # Update internal data from the current BidsFolder instead of reloading
            self._sync_data_from_bids_folder()

            self.subject_created.emit(subject_id)
            self.data_changed.emit()

            return True, ""

        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Failed to create subject: {str(e)}"

    def delete_subject(self, subject_id: str) -> bool:
        """
        Delete a subject from the dataset.

        Args:
            subject_id: Subject ID to delete

        Returns:
            True if deleted successfully
        """
        if not self._bids_folder:
            return False

        try:
            # Actually delete the subject from the BIDS dataset
            self._bids_folder.delete_bids_subject(subject_id)

            # Generate/update the participants.tsv file
            self._bids_folder.generate_participants_tsv()

            # Update internal data from the current BidsFolder
            self._sync_data_from_bids_folder()

            self.subject_deleted.emit(subject_id)
            self.data_changed.emit()

            return True

        except Exception:
            return False

    def update_subject_field(self, subject_id: str, field_name: str, new_value: str) -> bool:
        """
        Update a field for a subject.

        Args:
            subject_id: Subject ID to update
            field_name: Field name to update
            new_value: New field value

        Returns:
            True if updated successfully
        """
        if not self._bids_folder:
            return False

        try:
            # Get the actual BidsSubject object
            bids_subject = self._bids_folder.get_bids_subject(subject_id)
            if not bids_subject:
                return False

            # Special handling for subject_id changes
            if field_name == "subject_id":
                validation_service = ValidationService()
                is_valid, error = validation_service.validate_subject_name(new_value)
                if not is_valid:
                    QMessageBox.warning(
                        self._parent_widget,
                        "Invalid Subject ID",
                        error
                    )
                    return False

                # Check for duplicates in the actual BidsFolder
                if self._bids_folder.get_bids_subject(new_value):
                    QMessageBox.warning(
                        self._parent_widget,
                        "Duplicate Subject ID",
                        f"Subject ID '{new_value}' already exists"
                    )
                    return False

                # Actually update the subject ID in the BidsSubject
                bids_subject.set_subject_id(new_value)

                # Use the new subject ID for the signal
                subject_id = new_value

            else:
                # Update optional key in the BidsSubject
                bids_subject.update_optional_key(field_name, new_value)

            # Generate/update the participants.tsv file
            self._bids_folder.generate_participants_tsv()

            # Update internal data from the current BidsFolder
            self._sync_data_from_bids_folder()

            self.subject_updated.emit(subject_id)
            self.data_changed.emit()

            return True

        except Exception:
            # Log error appropriately in production
            return False

    def add_key_after(self, column_index: int) -> bool:
        """
        Add a new key/column after the specified column.

        Args:
            column_index: Index to add column after

        Returns:
            True if added successfully
        """
        if not self._bids_folder:
            return False

        key_name, ok = QInputDialog.getText(
            self._parent_widget,
            "Add Key",
            "Enter name for the new key:"
        )

        if not ok or not key_name.strip():
            return False

        key_name = key_name.strip()

        # Check if key already exists
        if key_name in self._all_optional_keys or key_name == "subject_id":
            QMessageBox.warning(
                self._parent_widget,
                "Duplicate Key",
                f"Key '{key_name}' already exists"
            )
            return False

        try:
            # Add key to all BidsSubject objects
            default_value = self._get_default_value_for_key(key_name)
            bids_subjects = self._bids_folder.get_bids_subjects()

            for subject in bids_subjects:
                if key_name not in subject.get_optional_keys():
                    # Use the BidsSubject method to add the key at specific position
                    subject.add_optional_key_at(column_index - 1, key_name, default_value)

            # Generate/update the participants.tsv file
            self._bids_folder.generate_participants_tsv()

            # Update internal data from the current BidsFolder
            self._sync_data_from_bids_folder()

            self.keys_updated.emit()
            self.data_changed.emit()

            return True

        except Exception:
            return False

    def add_key_before(self, column_index: int) -> bool:
        """
        Add a new key/column before the specified column.

        Args:
            column_index: Index to add column before

        Returns:
            True if added successfully
        """
        # For simplicity, use same logic as add_key_after
        # The actual positioning would be handled by the UI
        return self.add_key_after(column_index)

    def remove_key(self, key_name: str) -> bool:
        """
        Remove a key/column from the table.

        Args:
            key_name: Name of key to remove

        Returns:
            True if removed successfully
        """
        if not self._bids_folder:
            return False

        if key_name == "subject_id":
            QMessageBox.warning(
                self._parent_widget,
                "Cannot Remove",
                "Subject ID column cannot be removed"
            )
            return False

        # Ask for confirmation
        reply = QMessageBox.question(
            self._parent_widget,
            "Remove Key",
            f"Are you sure you want to remove the '{key_name}' key?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return False

        try:
            # Remove key from all BidsSubject objects
            bids_subjects = self._bids_folder.get_bids_subjects()
            for subject in bids_subjects:
                subject.remove_optional_key(key_name)

            # Generate/update the participants.tsv file
            self._bids_folder.generate_participants_tsv()

            # Update internal data from the current BidsFolder
            self._sync_data_from_bids_folder()

            self.keys_updated.emit()
            self.data_changed.emit()

            return True

        except Exception:
            return False

    def get_subjects_data(self) -> list[dict[str, Any]]:
        """
        Get all subjects data.

        Returns:
            List of subject dictionaries
        """
        return self._subjects_data.copy()

    def get_subject_data(self, subject_id: str) -> dict[str, Any] | None:
        """
        Get data for a specific subject.

        Args:
            subject_id: Subject ID to get data for

        Returns:
            Subject data dictionary or None if not found
        """
        for subject in self._subjects_data:
            if subject["subject_id"] == subject_id:
                return subject.copy()
        return None

    def get_all_keys(self) -> dict[str, str]:
        """
        Get all available keys with their default values.

        Returns:
            Dictionary of key names to default values
        """
        return self._all_optional_keys.copy()

    def get_subjects_keys_from_data(self) -> dict[str, str]:
        """
        Get subjects keys for table (excluding subject_id).

        Returns:
            Dictionary of keys to default values
        """
        keys = self._all_optional_keys.copy()
        # Remove subject_id if present
        keys.pop("Subject ID", None)
        return keys

    def get_table_data_matrix(self) -> tuple[list[str], list[list[str]]]:
        """
        Get table data in matrix format for UI display.

        Returns:
            Tuple of (column_headers, row_data)
        """
        if not self._subjects_data:
            return [], []

        # Get all unique keys from all subjects
        all_keys = set()
        all_keys.add("subject_id")
        for subject in self._subjects_data:
            all_keys.update(subject.keys())

        # Sort keys (subject_id first, then alphabetical)
        headers = ["subject_id"] + sorted([k for k in all_keys if k != "subject_id"])

        # Build rows
        rows = []
        for subject in self._subjects_data:
            row = []
            for header in headers:
                row.append(subject.get(header, ""))
            rows.append(row)

        return headers, rows

    def refresh_from_dataset(self) -> bool:
        """
        Refresh subjects data from the dataset.

        Returns:
            True if refreshed successfully
        """
        dataset_path = self._get_dataset_path()
        if not dataset_path:
            return False

        return self.load_subjects(dataset_path)

    def save_to_participants_file(self) -> bool:
        """
        Save current subjects data to participants.tsv file.

        Returns:
            True if saved successfully
        """
        if not self._bids_folder:
            return False

        try:
            # Use BidsFolder to regenerate participants.tsv
            self._bids_folder.generate_participants_tsv()
            return True

        except Exception:
            return False

