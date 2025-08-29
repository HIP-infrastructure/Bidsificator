"""Controller for batch subject import operations."""

from typing import List, Dict, Any, Optional, Tuple
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal

from ..models.SubjectDataModel import SubjectDataModel, SubjectData
from ..services.DataCrawlerService import DataCrawlerService
from ..workers.ImportBidsSubjectsWorker import ImportBidsSubjectsWorker


class ImportSubjectsController(QObject):
    """Controller for coordinating batch subject import operations."""
    
    # Signals for UI updates
    progress_updated = pyqtSignal(int)  # Progress value 0-100
    import_completed = pyqtSignal(dict)  # Import results
    import_failed = pyqtSignal(str)  # Error message
    subjects_loaded = pyqtSignal()  # Subject list updated
    selection_changed = pyqtSignal(int)  # Selected subject index changed
    file_list_updated = pyqtSignal()  # File list for selected subject updated
    
    def __init__(self, dataset_path_provider, file_editor_controller, parent: Optional[QWidget] = None):
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
        self._worker: Optional[ImportBidsSubjectsWorker] = None
        self._config_path = 'bidsificator/config/config.yaml'
    
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
    
    def parse_subjects_to_import(self, config_path: Optional[str] = None) -> bool:
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
            # Use model to crawl and load subjects
            self._model.crawl_and_load_subjects(self._config_path)
            
            # Emit signal for UI update
            self.subjects_loaded.emit()
            
            # Update file editor with first subject if available
            if self._model.count() > 0:
                self.selected_subject_index = 0
            
            return True
            
        except Exception as e:
            error_message = f"Failed to parse subjects: {str(e)}"
            QMessageBox.warning(
                self._parent_widget,
                "Parse Failed",
                error_message
            )
            self.import_failed.emit(error_message)
            return False
    
    def get_subject_ids(self) -> List[str]:
        """
        Get list of subject IDs.
        
        Returns:
            List of subject ID strings
        """
        return self._model.get_subject_ids()
    
    def get_selected_subject(self) -> Optional[SubjectData]:
        """
        Get currently selected subject.
        
        Returns:
            SubjectData instance or None if no selection
        """
        return self._model.get_selected_subject()
    
    def remove_selected_subjects(self, selected_indices: List[int]) -> bool:
        """
        Remove multiple selected subjects.
        
        Args:
            selected_indices: List of indices to remove
            
        Returns:
            True if any subjects were removed
        """
        if not selected_indices:
            return False
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self._parent_widget,
            "Remove Subject",
            "Are you sure you want to remove the selected subject(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
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
    
    def start_batch_import(self) -> bool:
        """
        Start the batch import process.
        
        Returns:
            True if started successfully
        """
        dataset_path = self._get_dataset_path()
        if not dataset_path:
            QMessageBox.warning(
                self._parent_widget,
                "No Dataset",
                "Please load a dataset first"
            )
            return False
        
        if self._model.is_empty():
            QMessageBox.warning(
                self._parent_widget,
                "No Subjects",
                "Please parse subjects first"
            )
            return False
        
        # Check if a worker is already running
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(
                self._parent_widget,
                "Import in Progress",
                "An import is already in progress"
            )
            return False
        
        # Validate all subjects before import
        all_valid, errors = self._model.validate_all_subjects()
        if not all_valid:
            error_message = "Validation errors found:\n" + "\n".join(errors)
            QMessageBox.warning(
                self._parent_widget,
                "Validation Failed",
                error_message
            )
            return False
        
        # Prepare subjects for import
        subjects_data = self._model.prepare_for_import()
        if not subjects_data:
            QMessageBox.warning(
                self._parent_widget,
                "No Valid Subjects",
                "No valid subjects found for import"
            )
            return False
        
        # Create and start worker
        self._worker = ImportBidsSubjectsWorker(dataset_path, subjects_data)
        self._worker.update_progressbar_signal.connect(self._on_progress_updated)
        self._worker.finished.connect(self._on_import_finished)
        self._worker.start()
        
        return True
    
    def _on_progress_updated(self, progress: int):
        """Handle progress update from worker."""
        self.progress_updated.emit(progress)
    
    def _on_import_finished(self):
        """Handle import completion from worker."""
        # Calculate results
        total_files = sum(len(subject.files) for subject in self._model.subjects)
        subject_count = self._model.count()
        
        results = {
            "subjects_imported": subject_count,
            "total_files": total_files,
            "success": True
        }
        
        self.import_completed.emit(results)
        
        # Clean up worker
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        
        # Show completion message
        QMessageBox.information(
            self._parent_widget,
            "Import Complete",
            f"Successfully imported {subject_count} subjects with {total_files} files.\n\n"
            "Check the dataset folder for the imported files."
        )
    
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
    
    def get_statistics(self) -> Dict[str, Any]:
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
    
    def get_subject_by_id(self, subject_id: str) -> Optional[SubjectData]:
        """
        Get subject by ID.
        
        Args:
            subject_id: Subject ID to find
            
        Returns:
            SubjectData instance or None if not found
        """
        return self._model.get_subject_by_id(subject_id)
    
    def set_config_path(self, config_path: str):
        """
        Set the configuration file path for data crawling.
        
        Args:
            config_path: Path to configuration file
        """
        self._config_path = config_path
    
    
    def update_subject_data(self, subject_id: str, modified_data: Dict[str, Any]) -> bool:
        """
        Update a subject's data with modified data from FileEditor.
        
        Args:
            subject_id: Subject ID to update
            modified_data: Modified subject data dictionary
            
        Returns:
            True if updated successfully
        """
        # Find the subject in our model
        for i, subject in enumerate(self._model.subjects):
            if subject.subject_id == subject_id:
                # Update the subject's files with the modified data
                subject.files = modified_data.get("files", [])
                return True
        
        return False