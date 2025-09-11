"""Controller for dataset creation, loading, and management operations."""

from typing import Tuple, Optional
from PyQt6.QtWidgets import QWidget, QFileDialog, QInputDialog, QMessageBox
from PyQt6.QtCore import QStandardPaths

from ..models.DatasetModel import DatasetModel
from ..services.ValidationServiceSchema import ValidationService
from ..ui.ValidationResultsDialog import ValidationProgressDialog, ValidationResultsDialog


class DatasetController:
    """Controller for coordinating dataset operations between model and UI."""
    
    def __init__(self, parent_widget: Optional[QWidget] = None):
        """
        Initialize dataset controller.
        
        Args:
            parent_widget: Parent widget for dialogs (optional)
        """
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
    
    def create_new_dataset(self) -> Tuple[bool, str]:
        """
        Create a new BIDS dataset with user interaction.
        
        Returns:
            Tuple of (success, error_message or dataset_path)
        """
        # Get folder path from user
        folder_path = QFileDialog.getExistingDirectory(
            self._parent_widget,
            "Select a folder to save the BIDS dataset",
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        )
        
        if not folder_path:
            return False, "No folder selected"
        
        # Get dataset name from user
        dataset_name, ok = QInputDialog.getText(
            self._parent_widget,
            "Dataset Name", 
            "Enter a name for the dataset"
        )
        
        if not ok or not dataset_name.strip():
            if not ok:
                return False, "Operation cancelled"
            else:
                QMessageBox.warning(
                    self._parent_widget,
                    "Dataset Name empty",
                    "Please enter a dataset name"
                )
                return False, "Empty dataset name"
        
        # Create the dataset using the model
        success, error_message = self._model.create_dataset(folder_path, dataset_name)
        
        if success:
            return True, self._model.dataset_path
        else:
            QMessageBox.warning(
                self._parent_widget,
                "Dataset Creation Failed",
                error_message
            )
            return False, error_message
    
    def load_existing_dataset(self) -> Tuple[bool, str]:
        """
        Load an existing BIDS dataset with user interaction.
        
        Returns:
            Tuple of (success, error_message or dataset_path)
        """
        # Get folder path from user
        folder_path = QFileDialog.getExistingDirectory(
            self._parent_widget,
            "Select a folder",
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        )
        
        if not folder_path:
            return False, "No folder selected"
        
        # Load the dataset using the model
        success, error_message = self._model.load_dataset(folder_path)
        
        if success:
            return True, self._model.dataset_path
        else:
            QMessageBox.warning(
                self._parent_widget,
                "Dataset Loading Failed", 
                error_message
            )
            return False, error_message
    
    def load_dataset_from_path(self, dataset_path: str) -> Tuple[bool, str]:
        """
        Load a dataset from a specific path.
        
        Args:
            dataset_path: Path to the dataset
            
        Returns:
            Tuple of (success, error_message)
        """
        return self._model.load_dataset(dataset_path)
    
    def create_subject(self, subject_name: str) -> Tuple[bool, str]:
        """
        Create a new subject in the current dataset.
        
        Args:
            subject_name: Name of the subject to create
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._model.is_loaded:
            error = "No dataset loaded"
            QMessageBox.warning(
                self._parent_widget,
                "No dataset selected",
                "Please open a BIDS dataset first"
            )
            return False, error
        
        if not subject_name:
            error = "Subject name cannot be empty"
            QMessageBox.warning(
                self._parent_widget,
                "Subject Name empty",
                "Please enter a subject name"
            )
            return False, error
        
        if not subject_name.startswith("sub-"):
            error = "Subject name should start with 'sub-'"
            QMessageBox.warning(
                self._parent_widget,
                "Subject Name not valid",
                error
            )
            return False, error
        
        # Use model to add the subject
        success, error_message = self._model.add_subject(subject_name)
        
        if not success:
            QMessageBox.warning(
                self._parent_widget,
                "Subject Creation Failed",
                error_message
            )
        
        return success, error_message
    
    def validate_dataset(self, subject_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate the current dataset or a specific subject.
        
        Args:
            subject_name: Optional subject to validate specifically
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not self._model.is_loaded:
            error = "No dataset loaded"
            QMessageBox.warning(
                self._parent_widget,
                "No Dataset found",
                "Please load a Dataset first"
            )
            return False, error
        
        # ValidationService already imported at top
        
        # Show progress dialog
        progress = ValidationProgressDialog(self._parent_widget)
        progress.show()
        
        try:
            # Update progress message
            if subject_name:
                progress.set_status(f"Validating subject {subject_name}...")
            else:
                progress.set_status("Validating entire dataset...")
            
            # Get detailed validation result
            validation_service = ValidationService()
            dataset_path = self._model.current_dataset.path
            
            if subject_name:
                # Subject-specific validation (no dataset-level checks)
                validation_result = validation_service.validate_subject(dataset_path, subject_name)
            else:
                # Full dataset validation (includes dataset-level checks)
                validation_result = validation_service.validate_dataset(dataset_path)
            
            # Close progress dialog
            progress.close()
            
            # Show detailed results dialog
            results_dialog = ValidationResultsDialog(self._parent_widget)
            results_dialog.display_validation_result(validation_result)
            results_dialog.exec()
            
            return validation_result.is_valid, validation_result.message
            
        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self._parent_widget,
                "Validation Error",
                f"An error occurred during validation: {str(e)}"
            )
            return False, str(e)
    
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
    
    def get_tree_model_path(self) -> Optional[str]:
        """
        Get dataset path for tree view model.
        
        Returns:
            Dataset path or None if no dataset loaded
        """
        return self._model.get_tree_model_data()
    
