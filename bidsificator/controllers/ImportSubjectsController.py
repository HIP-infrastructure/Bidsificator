"""Controller for batch subject import operations."""

import os
from typing import List, Dict, Any, Optional, Tuple
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal

from ..models.SubjectDataModel import SubjectDataModel, SubjectData
from ..services.DataCrawlerService import DataCrawlerService
from ..services.SubjectLookupService import SubjectLookupService
from ..workers.ImportBidsSubjectsWorker import ImportBidsSubjectsWorker
from ..workers.BidsSubjectsProcess import check_subject_conflicts


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
        # Use absolute path relative to the package location
        self._config_path = os.path.realpath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "config",
                "config.yaml"
            )
        )
        self._lookup_table_path: Optional[str] = None
        self._subject_mapping: Dict[str, str] = {}
    
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
            # Use model to crawl and load subjects with subject mapping
            self._model.crawl_and_load_subjects(self._config_path, self._subject_mapping)
            
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
    
    def get_display_names(self) -> List[str]:
        """
        Get list of display names for UI (original [mapped] format).
        
        Returns:
            List of display name strings
        """
        return self._model.get_display_names()
    
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
        
        # Check for subject conflicts before starting import
        try:
            existing_subjects = check_subject_conflicts(dataset_path, subjects_data)
            overwrite_existing = False
            
            if existing_subjects:
                # Show conflict resolution dialog
                conflict_result = self._show_conflict_resolution_dialog(existing_subjects)
                
                if conflict_result == "cancel":
                    return False  # User cancelled
                elif conflict_result == "overwrite":
                    overwrite_existing = True
                elif conflict_result == "skip":
                    overwrite_existing = False
                    # Filter out conflicting subjects
                    subjects_data = [s for s in subjects_data 
                                   if f"sub-{s['subject_id']}" not in existing_subjects]
                    
                    if not subjects_data:
                        QMessageBox.information(
                            self._parent_widget,
                            "No Subjects to Import",
                            "All subjects already exist and were skipped."
                        )
                        return False
        
        except Exception as e:
            QMessageBox.warning(
                self._parent_widget,
                "Error Checking Conflicts",
                f"Failed to check for existing subjects: {str(e)}"
            )
            return False
        
        # Create and start worker with overwrite setting
        self._worker = ImportBidsSubjectsWorker(dataset_path, subjects_data, overwrite_existing)
        self._worker.update_progressbar_signal.connect(self._on_progress_updated)
        self._worker.finished.connect(self._on_import_finished)
        self._worker.start()
        
        return True
    
    def _show_conflict_resolution_dialog(self, existing_subjects: List[str]) -> str:
        """
        Show dialog to resolve subject conflicts.
        
        Args:
            existing_subjects: List of existing subject IDs that conflict
            
        Returns:
            String indicating user choice: "cancel", "overwrite", or "skip"
        """
        subject_list = '\n'.join([f"• {subject}" for subject in existing_subjects])
        
        msg = QMessageBox(self._parent_widget)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Subject Conflicts Detected")
        
        if len(existing_subjects) == 1:
            msg.setText(f"The following subject already exists in the dataset:\n\n{subject_list}")
        else:
            msg.setText(f"The following {len(existing_subjects)} subjects already exist in the dataset:\n\n{subject_list}")
        
        msg.setInformativeText("How would you like to proceed?")
        
        # Add custom buttons
        overwrite_btn = msg.addButton("Overwrite Existing", QMessageBox.ButtonRole.AcceptRole)
        skip_btn = msg.addButton("Skip These Subjects", QMessageBox.ButtonRole.RejectRole) 
        cancel_btn = msg.addButton("Cancel Import", QMessageBox.ButtonRole.NoRole)
        
        msg.setDefaultButton(skip_btn)
        msg.exec()
        
        clicked_button = msg.clickedButton()
        
        if clicked_button == overwrite_btn:
            return "overwrite"
        elif clicked_button == skip_btn:
            return "skip"
        else:  # cancel or close
            return "cancel"

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
            self.lookup_table_updated.emit("Lookup table cleared")
            return True
        
        # Validate CSV format first
        is_valid, format_errors = SubjectLookupService.validate_csv_format(csv_path)
        if not is_valid:
            error_message = "CSV validation failed:\n" + "\n".join(format_errors)
            QMessageBox.warning(
                self._parent_widget,
                "Invalid Lookup Table",
                error_message
            )
            self.lookup_table_updated.emit("Invalid lookup table format")
            return False
        
        # Parse the CSV file
        mapping, parse_errors = SubjectLookupService.parse_lookup_table(csv_path)
        
        if parse_errors:
            error_message = "CSV parsing failed:\n" + "\n".join(parse_errors[:10])  # Limit errors shown
            if len(parse_errors) > 10:
                error_message += f"\n... and {len(parse_errors) - 10} more errors"
            
            QMessageBox.warning(
                self._parent_widget,
                "Lookup Table Parsing Error",
                error_message
            )
            self.lookup_table_updated.emit(f"Parsing failed: {len(parse_errors)} errors")
            return False
        
        # Successfully parsed
        self._lookup_table_path = csv_path
        self._subject_mapping = mapping
        
        status_message = f"Loaded {len(mapping)} subject mappings"
        self.lookup_table_updated.emit(status_message)
        
        # Show success message with preview
        preview_list = list(mapping.items())[:5]  # Show first 5 mappings
        preview_text = "\n".join([f"{orig} → {mapped}" for orig, mapped in preview_list])
        if len(mapping) > 5:
            preview_text += f"\n... and {len(mapping) - 5} more"
        
        QMessageBox.information(
            self._parent_widget,
            "Lookup Table Loaded",
            f"Successfully loaded {len(mapping)} subject mappings.\n\nPreview:\n{preview_text}"
        )
        
        return True
    
    def get_lookup_table_path(self) -> Optional[str]:
        """Get current lookup table path."""
        return self._lookup_table_path
    
    def has_lookup_table(self) -> bool:
        """Check if lookup table is loaded."""
        return bool(self._lookup_table_path and self._subject_mapping)
    
    def get_mapping_count(self) -> int:
        """Get number of mappings in lookup table."""
        return len(self._subject_mapping)
    
    def get_mapping_preview(self, limit: int = 10) -> List[Tuple[str, str]]:
        """
        Get preview of current mappings.
        
        Args:
            limit: Maximum number of mappings to return
            
        Returns:
            List of (original_id, mapped_name) tuples
        """
        return list(self._subject_mapping.items())[:limit]
    
    def create_lookup_template(self) -> bool:
        """
        Create a lookup table template file with file save dialog.
        
        Returns:
            True if template was created successfully
        """
        from PyQt6.QtWidgets import QFileDialog
        
        # Get current subject IDs for pre-population (if available)
        current_subject_ids = self.get_subject_ids() if self._model.count() > 0 else None
        
        # Show file save dialog
        suggested_filename = "lookup_table.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self._parent_widget,
            "Save Lookup Table Template",
            suggested_filename,
            "CSV files (*.csv);;All files (*.*)"
        )
        
        if not file_path:
            # User cancelled
            return False
        
        # Ensure .csv extension
        if not file_path.lower().endswith('.csv'):
            file_path += '.csv'
        
        # Create template file
        success, error_message = SubjectLookupService.create_template_file(file_path, current_subject_ids)
        
        if success:
            # Show success message
            subject_count = len(current_subject_ids) if current_subject_ids else 3
            if current_subject_ids:
                message = f"Template created successfully with {subject_count} pre-populated subject IDs.\n\nFile saved to:\n{file_path}\n\nPlease fill in the CenterName and NumericID columns."
            else:
                message = f"Template created successfully with example entries.\n\nFile saved to:\n{file_path}\n\nPlease replace the example data with your actual anonymous subject information."
            
            QMessageBox.information(
                self._parent_widget,
                "Template Created",
                message
            )
            
            # Update the lookup table path field to point to the new template
            self.lookup_table_updated.emit(f"Template created: {subject_count} entries")
            return True
        else:
            # Show error message
            QMessageBox.warning(
                self._parent_widget,
                "Template Creation Failed",
                f"Failed to create template file:\n\n{error_message}"
            )
            self.lookup_table_updated.emit("Template creation failed")
            return False