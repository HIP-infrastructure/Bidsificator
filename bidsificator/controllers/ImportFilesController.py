"""Controller for single file import tab operations."""

from typing import Dict, List, Tuple, Optional, Any
from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal

from ..models.ImportSessionModel import ImportSessionModel
from ..services.FileDetectionServiceSchema import FileDetectionService
from ..services.ImportService import ImportService
from ..workers.ImportBidsFilesWorker import ImportBidsFilesWorker


class ImportFilesController(QObject):
    """Controller for coordinating single file import operations."""
    
    # Signals for UI updates
    progress_updated = pyqtSignal(int)  # Progress value 0-100
    import_completed = pyqtSignal(dict)  # Import results
    import_failed = pyqtSignal(str)  # Error message
    file_list_changed = pyqtSignal()  # File list updated
    selection_changed = pyqtSignal(int)  # Selected file index changed
    form_data_updated = pyqtSignal(dict)  # Form data for selected file
    
    def __init__(self, dataset_path_provider, parent: Optional[QWidget] = None):
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
        self._worker: Optional[ImportBidsFilesWorker] = None
        self._browse_memory = ""
        self._contact_labeling_file: Optional[str] = None

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
    
    def add_multiple_files(self, form_defaults: Dict[str, str], memory_path: str = "") -> Tuple[int, List[str]]:
        """
        Add multiple files through file dialog.
        
        Args:
            form_defaults: Default form values to apply to files
            memory_path: Path to remember for file dialog
            
        Returns:
            Tuple of (successful_count, failed_files)
        """
        if memory_path:
            self._browse_memory = memory_path
        
        # Get file filter
        all_filter = FileDetectionService.get_all_supported_extensions()
        
        # Open multi-file selection dialog
        files, _ = QFileDialog.getOpenFileNames(
            self._parent_widget,
            "Select files to import",
            self._browse_memory or "",
            all_filter
        )
        
        if not files:
            return 0, []
        
        # Update browse memory
        if files:
            import os
            self._browse_memory = os.path.dirname(files[0])
        
        # Add files to the model
        successful_count, failed_files = self._model.add_files(files, form_defaults)
        
        # Emit signals for UI updates
        self.file_list_changed.emit()
        
        if successful_count > 0 and self._model.selected_file_index == -1:
            self.selected_file_index = 0
        
        # Show results to user
        if successful_count > 0 or failed_files:
            message = f"Successfully imported {successful_count} files"
            if failed_files:
                message += f"\n\nFailed files:\n" + "\n".join(failed_files)
            
            QMessageBox.information(
                self._parent_widget,
                "Import Results",
                message
            )
        
        return successful_count, failed_files
    
    def browse_single_file(self, modality: str) -> Optional[str]:
        """
        Browse for a single file based on modality.
        
        Args:
            modality: Current modality selection
            
        Returns:
            Selected file path or None if cancelled
        """
        filters = FileDetectionService.get_file_filters()
        
        # For anatomy, allow both file and folder selection
        if "(anat)" in modality:
            # First try file selection
            file_filter = filters.get("(anat)", "All files (*)")
            file_path, _ = QFileDialog.getOpenFileName(
                self._parent_widget,
                "Select a file (or Cancel to browse for DICOM folder)",
                self._browse_memory,
                file_filter
            )
            
            if file_path:
                import os
                self._browse_memory = os.path.dirname(file_path)
                return file_path
            else:
                # User cancelled file selection, offer folder selection for DICOM
                reply = QMessageBox.question(
                    self._parent_widget,
                    "DICOM Folder?",
                    "Do you want to select a DICOM folder instead?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    folder_path = QFileDialog.getExistingDirectory(
                        self._parent_widget,
                        "Select DICOM folder",
                        self._browse_memory
                    )
                    
                    if folder_path and FileDetectionService.is_dicom_folder(folder_path):
                        self._browse_memory = folder_path
                        return folder_path + " [DICOM Folder]"
                    elif folder_path:
                        QMessageBox.warning(
                            self._parent_widget,
                            "Not a DICOM folder",
                            "The selected folder doesn't appear to contain DICOM files."
                        )
                        
        elif any(key in modality for key in filters):
            # Regular file selection for other modalities
            file_filter = next(filter for key, filter in filters.items() if key in modality)
            file_path, _ = QFileDialog.getOpenFileName(
                self._parent_widget,
                "Select a file",
                self._browse_memory,
                file_filter
            )
            
            if file_path:
                import os
                self._browse_memory = os.path.dirname(file_path)
                return file_path
        else:
            QMessageBox.warning(
                self._parent_widget,
                "Modality not recognized",
                "Please select a modality first"
            )
        
        return None
    
    def remove_selected_file(self) -> bool:
        """
        Remove currently selected file from import list.
        
        Returns:
            True if removed successfully
        """
        if self._model.selected_file_index == -1:
            QMessageBox.warning(
                self._parent_widget,
                "No Selection",
                "Please select a file to remove"
            )
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
    
    def update_selected_file_from_form(self, form_data: Dict[str, str]) -> bool:
        """
        Update selected file with form data.
        
        Args:
            form_data: Dictionary with form field values
            
        Returns:
            True if updated successfully
        """
        return self._model.update_selected_file_from_form(form_data)
    
    def change_subject(self, new_subject: str, ask_user: bool = True) -> bool:
        """
        Change subject for all files in session.
        
        Args:
            new_subject: New subject ID
            ask_user: Whether to ask user for confirmation if files exist
            
        Returns:
            True if changed successfully
        """
        current_subject = self._model.file_model.current_subject
        
        # If no files or same subject, just update
        if (self._model.file_model.is_empty() or 
            current_subject == new_subject):
            return self._model.change_subject(new_subject)
        
        # If files exist and asking user is enabled
        if ask_user and not self._model.file_model.is_empty():
            reply = QMessageBox.question(
                self._parent_widget,
                "Subject Changed",
                f"You're switching from '{current_subject}' to '{new_subject}'.\n\n"
                f"What would you like to do with the {self.file_count} files in the list?\n\n"
                f"• YES: Update all files to use '{new_subject}'\n"
                f"• NO: Cancel - keep '{current_subject}' selected",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.No:
                return False  # User cancelled the change
        
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

        except Exception as e:
            print(f"Could not check for existing electrodes.tsv: {e}")
            return False

    def start_import(self) -> bool:
        """
        Start the import process.
        
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
        
        if not self._model.start_import():
            QMessageBox.warning(
                self._parent_widget,
                "Import Failed",
                self._model.error_message or "Cannot start import"
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
        
        # Prepare data for worker
        legacy_data = self._model.get_legacy_data_structure()
        subject_name = legacy_data["subject_id"]
        files = legacy_data["files"]

        # Check if we need to warn about electrodes.tsv regeneration
        if self._contact_labeling_file:
            if self._check_electrodes_will_be_overwritten(dataset_path, subject_name):
                # Show confirmation dialog
                reply = QMessageBox.question(
                    self._parent_widget,
                    "Regenerate electrodes.tsv?",
                    f"⚠️ The subject '{subject_name}' already has an existing electrodes.tsv file.\n\n"
                    f"Importing with a contact labeling file will completely regenerate "
                    f"this file with the clinical annotations.\n\n"
                    f"⚠️ Warning: Any manual edits to the existing electrodes.tsv will be LOST.\n\n"
                    f"Do you want to continue and regenerate?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No  # Default to No for safety
                )

                if reply == QMessageBox.StandardButton.No:
                    # User cancelled
                    return False

        # Create and start worker with optional contact labeling file
        self._worker = ImportBidsFilesWorker(
            dataset_path,
            subject_name,
            files,
            self._contact_labeling_file
        )
        self._worker.update_progressbar_signal.connect(self._on_progress_updated)
        self._worker.finished.connect(self._on_import_finished)
        self._worker.start()
        
        return True
    
    def _on_progress_updated(self, progress: int):
        """Handle progress update from worker."""
        self._model.progress = progress
        self.progress_updated.emit(progress)
    
    def _on_import_finished(self):
        """Handle import completion from worker."""
        # Prepare results
        results = {
            "files_imported": self.file_count,
            "subject": self.current_subject,
            "success": True
        }
        
        self._model.complete_import(results)
        self.import_completed.emit(results)
        
        # Clean up worker
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        
        # Show completion message
        QMessageBox.information(
            self._parent_widget,
            "Import Complete",
            f"Successfully imported {self.file_count} files.\n\n"
            "Files remain in the list for review. You can:\n"
            "• Check/modify any file settings\n"
            "• Remove files if needed\n"
            "• Add more files\n"
            "• Re-import if there were issues"
        )
    
    def get_ui_requirements_for_modality(self, modality: str) -> Dict[str, bool]:
        """
        Get UI visibility requirements for a modality.
        
        Args:
            modality: Modality string
            
        Returns:
            Dictionary with UI element visibility flags
        """
        return FileDetectionService.get_modality_requirements(modality)
    
    def clear_session(self):
        """Clear the current import session."""
        self._model.reset_session()
        self.file_list_changed.emit()
        self.selection_changed.emit(-1)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of current session.
        
        Returns:
            Dictionary with session information
        """
        return self._model.get_session_summary()
    
    def get_file_names_for_list_widget(self) -> List[str]:
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
    
    
    def set_files_data(self, subject_id: str, files_data: List[Dict], contact_labeling_file: Optional[str] = None) -> None:
        """
        Set files data directly from external source (e.g., MainWindow).

        Args:
            subject_id: Subject identifier
            files_data: List of file data dictionaries
            contact_labeling_file: Optional path to contact labeling Excel file
        """
        # Store contact labeling file
        self._contact_labeling_file = contact_labeling_file

        # Load the data into the model
        data = {
            "subject_id": subject_id,
            "files": files_data
        }
        self._model.load_from_legacy_data(data)
        self.file_list_changed.emit()
        if self._model.file_model.count() > 0:
            self.selected_file_index = 0