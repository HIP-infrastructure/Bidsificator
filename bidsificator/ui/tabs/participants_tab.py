"""Participants tab behaviour for MainWindow (mixed into MainWindow).

Covers subject creation, the read-only file-tree view, and the tree
context-menu operations (validate / rename / delete subjects and files). `self`
is the live MainWindow; see `bidsificator.ui.tabs` for the arrangement.
"""

import logging
import os

from PyQt6.QtGui import QCursor, QFileSystemModel
from PyQt6.QtWidgets import QInputDialog, QMenu, QMessageBox

from ...core.BidsFolder import BidsFolder
from ...services.ValidationServiceSchema import ValidationService

logger = logging.getLogger(__name__)


class ParticipantsTabMixin:
    """MainWindow slots/helpers for the Participants tab."""

    def create_subject(self):
        """Create a new subject using the controller."""
        subject_name = self.SubjectLineEdit.text().strip()

        if not subject_name:
            return  # Don't create empty subjects

        # Strip "sub-" prefix if user included it (case-insensitive)
        if subject_name.lower().startswith("sub-"):
            subject_name = subject_name[4:]

        # Create subject using PatientTableWidget controller
        if self.tableWidget._controller:
            success, error = self.tableWidget._controller.create_subject(subject_name)
            if success:
                # Clear the input field after successful creation
                self.SubjectLineEdit.clear()
                # Update the dropdown will be handled by signals
            else:
                # Show error message if creation failed
                QMessageBox.warning(self, "Create Subject Failed", error)

    def validate_bids_dataset(self):
        """Validate entire BIDS dataset using the controller."""
        # Validate the entire dataset, not just a single subject
        self._main_controller.validate_bids_dataset(subject_name=None)

    def load_treeView_UI(self, initial_folder):
        # Define file system model at the root folder chosen by the user
        m_localFileSystemModel = QFileSystemModel()
        m_localFileSystemModel.setReadOnly(True)
        m_localFileSystemModel.setRootPath(initial_folder)

        # set model in treeview
        self.fileTreeView.setModel(m_localFileSystemModel)
        # Show only what is under this path
        self.fileTreeView.setRootIndex(m_localFileSystemModel.index(initial_folder))
        # Show everything put starts at the given model index
        # self.fileTreeView.setCurrentIndex(m_localFileSystemModel.index(test_path));

        # //==[Ui Layout]
        self.fileTreeView.setAnimated(False)
        self.fileTreeView.setIndentation(20)
        # Sorting enabled puts elements in reverse (last is first, first is last)
        # self.fileTreeView.setSortingEnabled(True);
        # Hide name, file size, file type , etc
        self.fileTreeView.hideColumn(1)
        self.fileTreeView.hideColumn(2)
        self.fileTreeView.hideColumn(3)
        self.fileTreeView.header().hide()

    def show_file_tree_context_menu(self, position):
        """Show context menu for file tree items."""
        index = self.fileTreeView.indexAt(position)
        if not index.isValid():
            return

        selected_subjects, selected_files = self._get_selected_tree_items(index)

        if not selected_subjects and not selected_files:
            return

        if not self._validate_tree_selection(selected_subjects, selected_files):
            return

        if not self._check_dataset_operations_allowed():
            return

        context_menu = self._create_tree_context_menu(selected_subjects, selected_files)
        context_menu.popup(QCursor.pos())

    def _get_selected_tree_items(self, index):
        """Get selected subjects and files from tree view."""
        model = self.fileTreeView.model()
        selected_indexes = self.fileTreeView.selectionModel().selectedRows()
        if not selected_indexes:
            selected_indexes = [index]

        selected_subjects = []
        selected_files = []

        for idx in selected_indexes:
            file_path = model.filePath(idx)
            file_name = model.fileName(idx)

            if model.isDir(idx) and file_name.startswith("sub-"):
                selected_subjects.append({
                    'name': file_name,
                    'path': file_path,
                    'index': idx
                })
            elif not model.isDir(idx):
                selected_files.append({
                    'name': file_name,
                    'path': file_path,
                    'index': idx
                })

        return selected_subjects, selected_files

    def _validate_tree_selection(self, selected_subjects, selected_files):
        """Validate that tree selection is appropriate for context menu."""
        if selected_subjects and selected_files:
            QMessageBox.information(
                self,
                "Mixed Selection",
                "Please select either subjects or files, not both.\n\n"
                "This prevents accidental deletions."
            )
            return False
        return True

    def _check_dataset_operations_allowed(self):
        """Check if dataset operations are allowed based on validation level."""
        if self._validation_level == "NOT_BIDS":
            QMessageBox.warning(
                self,
                "Operations Not Available",
                "Please load a valid BIDS dataset to enable operations."
            )
            return False
        elif self._validation_level == "PARTIAL_BIDS":
            reply = QMessageBox.question(
                self,
                "Partial BIDS Dataset",
                "This dataset has validation issues. Continue with operation?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
        return True

    def _create_tree_context_menu(self, selected_subjects, selected_files):
        """Create context menu based on selected items."""
        context_menu = QMenu(self)

        if selected_subjects:
            self._add_subject_menu_actions(context_menu, selected_subjects)
        elif selected_files:
            self._add_file_menu_actions(context_menu, selected_files)

        return context_menu

    def _add_subject_menu_actions(self, menu, selected_subjects):
        """Add menu actions for selected subjects."""
        if len(selected_subjects) == 1:
            # Single subject - add validate and rename options
            validate_action = menu.addAction("Validate Subject")
            validate_action.triggered.connect(lambda: self.validate_subject_from_tree(selected_subjects[0]))

            menu.addSeparator()

            rename_action = menu.addAction("Rename Subject")
            rename_action.triggered.connect(lambda: self.rename_subject_from_tree(selected_subjects[0]))

        # Add delete action
        delete_text = "Delete Subject" if len(selected_subjects) == 1 else f"Delete {len(selected_subjects)} Subjects"
        delete_action = menu.addAction(delete_text)
        delete_action.triggered.connect(lambda: self.delete_subjects_from_tree(selected_subjects))

    def _add_file_menu_actions(self, menu, selected_files):
        """Add menu actions for selected files."""
        delete_text = "Delete File" if len(selected_files) == 1 else f"Delete {len(selected_files)} Files"
        delete_action = menu.addAction(delete_text)
        delete_action.triggered.connect(lambda: self.delete_files_from_tree(selected_files))

    def validate_subject_from_tree(self, subject_info):
        """Validate a specific BIDS subject from the file tree."""
        subject_name = subject_info['name']

        # Call the controller to validate this specific subject
        self._main_controller.validate_bids_dataset(subject_name=subject_name)

    def rename_subject_from_tree(self, subject_info):
        """Rename a BIDS subject from the file tree."""
        old_folder_name = subject_info['name']
        # Strip "sub-" prefix to get clean subject ID
        old_subject_id = (
            old_folder_name.replace("sub-", "", 1)
            if old_folder_name.startswith("sub-") else old_folder_name
        )

        # Prompt user for new subject ID
        new_subject_id, ok = QInputDialog.getText(
            self,
            "Rename Subject",
            f"Enter new name for subject '{old_subject_id}':",
            text=old_subject_id
        )

        if not ok or not new_subject_id.strip():
            return

        new_subject_id = new_subject_id.strip()

        # Strip "sub-" prefix if user included it (case-insensitive)
        if new_subject_id.lower().startswith("sub-"):
            new_subject_id = new_subject_id[4:]

        if new_subject_id == old_subject_id:
            return  # No change

        # Validate new subject ID
        validation_service = ValidationService()
        is_valid, error = validation_service.validate_subject_name(new_subject_id)
        if not is_valid:
            QMessageBox.warning(self, "Invalid Subject ID", error)
            return

        # Check if dataset is loaded and get BidsFolder
        if not self._main_controller.is_dataset_loaded():
            QMessageBox.warning(self, "No Dataset", "No dataset is currently loaded")
            return

        # Use the PatientTableController to rename the subject
        if self.tableWidget._controller:
            # First check if new subject ID already exists
            dataset_path = self._get_dataset_path()
            if not dataset_path:
                QMessageBox.warning(self, "Error", "Could not get dataset path")
                return

            bids_folder = BidsFolder(dataset_path)
            if bids_folder.get_bids_subject(new_subject_id):
                QMessageBox.warning(
                    self,
                    "Duplicate Subject ID",
                    f"Subject ID '{new_subject_id}' already exists"
                )
                return

            # Perform the rename using the controller
            success = self.tableWidget._controller.update_subject_field(
                old_subject_id, "subject_id", new_subject_id
            )

            if success:
                QMessageBox.information(
                    self,
                    "Subject Renamed",
                    f"Subject '{old_subject_id}' has been renamed to '{new_subject_id}'"
                )
                # UI update will be handled by the controller signals
            else:
                QMessageBox.critical(
                    self,
                    "Rename Failed",
                    f"Failed to rename subject '{old_subject_id}'"
                )

    def delete_subjects_from_tree(self, subjects_info):
        """Delete BIDS subjects from the file tree."""
        if not subjects_info:
            return

        # Check if dataset is loaded
        if not self._main_controller.is_dataset_loaded():
            QMessageBox.warning(self, "No Dataset", "No dataset is currently loaded")
            return

        # Prepare confirmation message
        if len(subjects_info) == 1:
            subject_folder_name = subjects_info[0]['name']
            subject_name = (
                subject_folder_name.replace("sub-", "", 1)
                if subject_folder_name.startswith("sub-") else subject_folder_name
            )
            message = f"Are you sure you want to delete subject '{subject_name}'?\n\n" \
                     f"This will permanently delete the subject folder and all its files."
            title = "Delete Subject"
        else:
            subject_names = []
            for s in subjects_info:
                folder_name = s['name']
                clean_name = folder_name.replace("sub-", "", 1) if folder_name.startswith("sub-") else folder_name
                subject_names.append(clean_name)
            message = f"Are you sure you want to delete {len(subjects_info)} subjects?\n\n" \
                     f"Subjects: {', '.join(subject_names)}\n\n" \
                     f"This will permanently delete all subject folders and their files."
            title = "Delete Multiple Subjects"

        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # Default to No for safety
        )

        if reply == QMessageBox.StandardButton.No:
            return

        # Perform deletions using the PatientTableController
        if not self.tableWidget._controller:
            QMessageBox.critical(self, "Error", "Table controller not available")
            return

        failed_deletions = []
        successful_deletions = []

        for subject_info in subjects_info:
            subject_folder_name = subject_info['name']
            # Strip "sub-" prefix to get clean subject ID
            subject_id = (
                subject_folder_name.replace("sub-", "", 1)
                if subject_folder_name.startswith("sub-") else subject_folder_name
            )
            success = self.tableWidget._controller.delete_subject(subject_id)

            if success:
                successful_deletions.append(subject_id)
            else:
                failed_deletions.append(subject_id)

        # Show results
        if successful_deletions and not failed_deletions:
            if len(successful_deletions) == 1:
                QMessageBox.information(
                    self,
                    "Subject Deleted",
                    f"Subject '{successful_deletions[0]}' has been deleted successfully"
                )
            else:
                QMessageBox.information(
                    self,
                    "Subjects Deleted",
                    f"{len(successful_deletions)} subjects have been deleted successfully"
                )
        elif failed_deletions:
            error_msg = f"Failed to delete: {', '.join(failed_deletions)}"
            if successful_deletions:
                error_msg = f"Partial success. Successfully deleted: {', '.join(successful_deletions)}\n" + error_msg
            QMessageBox.critical(self, "Deletion Failed", error_msg)

        # UI update will be handled by the controller signals

    def delete_files_from_tree(self, files_info):
        """Delete files from the file tree."""
        if not files_info:
            return

        # Prepare confirmation message
        if len(files_info) == 1:
            file_name = files_info[0]['name']
            message = f"Are you sure you want to delete the file '{file_name}'?\n\n" \
                     f"This action cannot be undone."
            title = "Delete File"
        else:
            file_names = [f['name'] for f in files_info[:5]]  # Show first 5 files
            if len(files_info) > 5:
                file_names.append(f"... and {len(files_info) - 5} more")
            message = f"Are you sure you want to delete {len(files_info)} files?\n\n" \
                     f"Files:\n{chr(10).join('• ' + name for name in file_names)}\n\n" \
                     f"This action cannot be undone."
            title = "Delete Multiple Files"

        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # Default to No for safety
        )

        if reply == QMessageBox.StandardButton.No:
            return

        # Perform the deletions in the model/controller; the view only maps the
        # resulting paths back to the display names it already knows.
        name_by_path = {f['path']: f['name'] for f in files_info}
        paths = [f['path'] for f in files_info]
        deleted_paths, failed = self._main_controller.delete_dataset_files(paths)

        successful_deletions = [
            name_by_path.get(p, os.path.basename(p)) for p in deleted_paths
        ]
        failed_deletions = [
            (name_by_path.get(p, os.path.basename(p)), reason) for p, reason in failed
        ]

        # Show results
        if successful_deletions and not failed_deletions:
            if len(successful_deletions) == 1:
                QMessageBox.information(
                    self,
                    "File Deleted",
                    f"File '{successful_deletions[0]}' has been deleted successfully"
                )
            else:
                QMessageBox.information(
                    self,
                    "Files Deleted",
                    f"{len(successful_deletions)} files have been deleted successfully"
                )
        elif failed_deletions:
            error_msg = "Failed to delete:\n"
            for name, reason in failed_deletions:
                error_msg += f"• {name}: {reason}\n"
            if successful_deletions:
                error_msg = f"Partial success. Successfully deleted {len(successful_deletions)} files.\n\n" + error_msg
            QMessageBox.critical(self, "Deletion Failed", error_msg)
