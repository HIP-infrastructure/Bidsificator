"""Import Subjects tab behaviour for MainWindow (mixed into MainWindow).

Covers subject parsing, the subject list and its embedded FileEditor (syncing
edits back to the ImportSubjectsController), the lookup table, and starting a
batch import. `self` is the live MainWindow; see `bidsificator.ui.tabs` for the
arrangement.
"""

import logging
import os

from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QFileDialog, QMenu

from ...core.BidsUtilityFunctions import BidsUtilityFunctions

logger = logging.getLogger(__name__)


class ImportSubjectsTabMixin:
    """MainWindow slots/helpers for the Import Subjects tab."""

    def _on_subjects_loaded(self):
        """Handle subjects loaded from import subjects controller."""
        self.IS_SubjectListWidget.clear()
        # Use display names for third tab to show "OriginalID [MappedID]" format
        display_names = self._main_controller.import_subjects_controller.get_display_names()
        for display_name in display_names:
            self.IS_SubjectListWidget.addItem(display_name)

        # Auto-select first subject if available, otherwise clear file editor
        if display_names:
            self.IS_SubjectListWidget.setCurrentRow(0)
            # Manually trigger the selection update since setCurrentRow doesn't always fire signals
            self.update_import_subject_fileList()
        else:
            # No subjects left - clear the file editor
            self._import_subject_file_editor.clear_file_list()

    def _on_import_subject_selection_changed(self, index: int):
        """Handle import subject selection change from controller."""
        # This will be handled by the controller updating the file editor
        pass

    def _on_lookup_table_updated(self, message: str):
        """Handle lookup table update message from controller."""
        # Update status or provide visual feedback
        # For now, just update the statusbar or show in console
        logger.debug("Lookup table status: %s", message)

    def parse_subject_to_import(self):
        """Parse subjects for import using the controller."""
        config_path = BidsUtilityFunctions.get_config_path()
        self._main_controller.parse_subjects_to_import(config_path)
        # UI update will be handled by controller signal

    def update_import_subject_fileList(self):
        """Update import subject file list using controller data."""
        selectedIndexes = self.IS_SubjectListWidget.selectedIndexes()
        if len(selectedIndexes) > 0:
            selected_row = selectedIndexes[0].row()

            # First, save current FileEditor data back to ImportSubjectsController
            self._sync_file_editor_to_import_controller()

            self._import_subject_file_editor.clear_file_list()

            # Get subject data from controller using row index
            subject_data = self._main_controller.import_subjects_controller.model.get_subject(selected_row)
            if subject_data:
                # Convert dataclass to dictionary for FileEditor
                from dataclasses import asdict
                legacy_format = asdict(subject_data)
                self._import_subject_file_editor.add_files_to_list(legacy_format)

    def _sync_file_editor_to_import_controller(self):
        """Sync FileEditor changes back to ImportSubjectsController."""
        # Save any pending form changes first
        if hasattr(self._import_subject_file_editor, '_save_form_data'):
            self._import_subject_file_editor._save_form_data()

        # Get the current subject data from FileEditor controller
        if (hasattr(self._import_subject_file_editor, '_controller') and
            hasattr(self._import_subject_file_editor._controller, '_current_subject_data')):

            modified_data = self._import_subject_file_editor._controller._current_subject_data
            if modified_data and modified_data.get("subject_id"):
                subject_id = modified_data.get("subject_id")

                # Update the ImportSubjectsController with modified data
                self._main_controller.import_subjects_controller.update_subject_data(subject_id, modified_data)

    def show_delete_import_subject_context_menu(self):
        # Create custom context menu
        self.customMenu = QMenu(self)
        deleteSelectedSubjectAction = self.customMenu.addAction("Remove Selected Subject(s)")
        deleteSelectedSubjectAction.triggered.connect(self.remove_selected_import_subject)
        # Enable/Disable the action based on the number of selected items
        selectedIndexes = self.IS_SubjectListWidget.selectedIndexes()
        self.customMenu.setEnabled(len(selectedIndexes) != 0)
        # Show the context menu
        self.customMenu.popup(QCursor.pos())

    def remove_selected_import_subject(self):
        """Remove selected subjects from import list using controller."""
        selectedIndexes = self.IS_SubjectListWidget.selectedIndexes()
        if not selectedIndexes:
            return

        # Get the row indices to remove
        indices_to_remove = [index.row() for index in selectedIndexes]

        # Use controller to remove subjects
        self._main_controller.remove_selected_import_subjects(indices_to_remove)

    def start_subjects_import(self):
        """Start subjects import using the controller."""

        # Reset progress bar for this tab
        self.IS_progressBar.setValue(0)

        # Show starting message in status bar
        self._status_bar_manager.show_progress("Batch import in progress...")

        # Save any pending FileEditor changes before import
        self._save_file_editor_changes()

        # Get task value from the FileEditor's TaskComboBox
        task = self._import_subject_file_editor.TaskComboBox.currentText()

        self._main_controller.start_subjects_import(task)

    def _save_file_editor_changes(self):
        """Save FileEditor changes back to ImportSubjectsController."""
        # Force save of any pending form changes (even if user didn't click "Save")
        if hasattr(self._import_subject_file_editor, '_save_form_data'):
            self._import_subject_file_editor._save_form_data()

        # Also update any changed fields from the form directly
        if hasattr(self._import_subject_file_editor, '_save_form_data_to_controller'):
            self._import_subject_file_editor._save_form_data_to_controller()

        # Get the modified data from FileEditor controller and sync to ImportSubjectsController
        if (hasattr(self._import_subject_file_editor, '_controller')
                and hasattr(self._import_subject_file_editor._controller, '_current_subject_data')):
            modified_data = self._import_subject_file_editor._controller._current_subject_data
            if modified_data and modified_data.get("subject_id"):
                subject_id = modified_data.get("subject_id")
                # Sync changes back to ImportSubjectsController before import
                self._main_controller.import_subjects_controller.update_subject_data(subject_id, modified_data)

    def browse_lookup_table(self):
        """Browse for CSV lookup table file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Lookup Table CSV File",
            self._browse_folder_path_memory,
            "CSV files (*.csv *.txt);;All files (*.*)"
        )

        if file_path:
            self._browse_folder_path_memory = os.path.dirname(file_path)
            self.lineEdit.setText(file_path)
            # The textChanged signal will trigger the controller update

    def on_lookup_table_path_changed(self, path: str):
        """Handle lookup table path change."""
        # Update controller when path changes
        self._main_controller.import_subjects_controller.set_lookup_table(path.strip())

    def create_lookup_template(self):
        """Create a lookup table template file."""
        self._main_controller.import_subjects_controller.create_lookup_template()
