import logging
import os

from PyQt6.QtCore import QStandardPaths, Qt
from PyQt6.QtGui import QCursor, QFileSystemModel
from PyQt6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
)

from ..controllers.MainController import MainController
from ..core.BidsFolder import BidsFolder
from ..forms.MainWindow_ui import Ui_MainWindow
from ..services.ValidationServiceSchema import ValidationService
from ..ui.AboutDialog import AboutDialog
from ..ui.OptionWindow import OptionWindow
from ..ui.StatusBarManager import StatusBarManager
from ..ui.tabs.import_files_tab import ImportFilesTab
from ..ui.tabs.import_subjects_tab import ImportSubjectsTab
from ..ui.tabs.participants_tab import ParticipantsTab
from ..ui.ValidationResultsDialog import ValidationProgressDialog, ValidationResultsDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow, Ui_MainWindow):
    """Main application window — a thin host (per-tab `.ui` split complete, 9d.3).

    All three tabs are self-contained `QWidget`s built from their own `.ui`
    (`ParticipantsTab` / `ImportFilesTab` / `ImportSubjectsTab`); this class
    constructs them, inserts them into the (otherwise empty) tab widget, and
    wires the cross-tab signals. It also owns the window chrome that lives
    outside the tab widget: the menu, the status bar, dataset create/open, the
    validation state, and the left-pane file-tree browser + BIDS-validator
    button (whose context-menu operations reach the subject controller through
    `ParticipantsTab.subject_controller`).
    """

    _browse_folder_path_memory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
    __optionWindow = None

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Initialize status bar manager
        self._status_bar_manager = StatusBarManager(self.statusbar)

        # Set up splitter with reasonable default sizes
        # 25% for file tree, 75% for main content
        self.mainSplitter.setSizes([300, 700])

        # BIDS validation state
        self._is_valid_bids_dataset = False
        self._validation_level = "NOT_BIDS"
        self._validation_issues = []

        # Initialize MVC Controller
        self._main_controller = MainController(self)
        self._setup_controller_connections()

        # Every tab is a self-contained QWidget owning its widgets + behaviour and
        # wiring its own controller signals. They take their dependencies by
        # injection and are inserted into the empty tab widget in ASCENDING index
        # order (QTabWidget.insertTab clamps the index to count()).
        self._participants_tab = ParticipantsTab(self._main_controller)
        self.tabWidget.insertTab(0, self._participants_tab, "Participants")

        self._import_files_tab = ImportFilesTab(
            self._main_controller,
            self._status_bar_manager,
            self._get_browse_memory,
            self._set_browse_memory,
        )
        self.tabWidget.insertTab(1, self._import_files_tab, "Import Files")

        self._import_subjects_tab = ImportSubjectsTab(
            self._main_controller,
            self._status_bar_manager,
            self._get_browse_memory,
            self._set_browse_memory,
        )
        self.tabWidget.insertTab(2, self._import_subjects_tab, "Import Subjects")

        # Cross-tab: a subject added/renamed/removed on the Participants tab must
        # refresh the DatasetController's subject list (→ subjects_updated) and the
        # Import Files subject dropdown.
        self._participants_tab.subject_updated.connect(self._notify_main_controller_subjects_changed)
        self._participants_tab.subject_updated.connect(self._import_files_tab.refresh_subject_dropdown)

        # Connect Menu
        self.actionNew_Bids_Dataset.triggered.connect(self.create_dataset)
        self.actionOpen_Bids_Dataset.triggered.connect(self.open_dataset)
        self.actionDatabase_Configuration.triggered.connect(self.open_db_options)
        self.actionAbout.triggered.connect(self.show_about_dialog)

        # File-tree browser (left splitter pane — window chrome)
        self.fileTreeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.fileTreeView.customContextMenuRequested.connect(self.show_file_tree_context_menu)
        # Enable multi-selection in file tree for subject operations
        self.fileTreeView.setSelectionMode(self.fileTreeView.SelectionMode.ExtendedSelection)

        # BIDS-validator button (left pane — window chrome)
        self.BidsValidatorPushButton.clicked.connect(self.validate_bids_dataset)

    def _get_dataset_path(self) -> str:
        """Get current dataset path (used by the file-tree rename op)."""
        if hasattr(self, '_main_controller') and self._main_controller:
            return self._main_controller.dataset_controller.dataset_path
        return ""

    def _get_browse_memory(self) -> str:
        """Shared 'last browsed folder' memory (injected into the import tabs)."""
        return self._browse_folder_path_memory

    def _set_browse_memory(self, path: str):
        """Update the shared 'last browsed folder' memory."""
        self._browse_folder_path_memory = path

    def _notify_main_controller_subjects_changed(self):
        """Notify MainController that subjects have changed so it can emit its signal."""
        if hasattr(self, '_main_controller') and self._main_controller:
            # Refresh the subjects list in the DatasetController first
            self._main_controller.dataset_controller.refresh_subjects()
            # Then emit the signal to update the dropdown
            self._main_controller.subjects_updated.emit()

    def _setup_controller_connections(self):
        """Set up connections between controllers and UI."""
        # Dataset controller signals
        self._main_controller.dataset_changed.connect(self._on_dataset_changed)
        self._main_controller.subjects_updated.connect(self._on_subjects_updated)

        # DatasetController is UI-free and reports back via signals; the view owns
        # the dialogs. Progress dialog for validation is held here so it can be
        # closed both on completion and on error.
        self._validation_progress_dialog = None
        dataset_ctrl = self._main_controller.dataset_controller
        dataset_ctrl.operation_failed.connect(self._on_dataset_operation_failed)
        dataset_ctrl.validation_started.connect(self._on_validation_started)
        dataset_ctrl.validation_finished.connect(self._on_validation_finished)

        # The three tabs wire their own controller signals inside their QWidget classes.

    def _on_dataset_changed(self, dataset_path: str):
        """Handle dataset change from controller."""
        # Update validation state and tabs
        self._update_validation_state()
        self.load_treeView_UI(dataset_path)
        self._update_tabs_based_on_validation()

        # Only load subjects and update UI if it's a valid dataset
        if self._validation_level != "NOT_BIDS":
            self._participants_tab.refresh_table(dataset_path)
            self._import_files_tab.refresh_subject_dropdown()

        # Show validation warning if necessary
        self._show_validation_warning_if_needed()

    def _on_subjects_updated(self):
        """Handle subjects update from controller - refreshes both table and dropdown."""
        # Update the subject table (Participants tab)
        dataset_path = self._get_dataset_path()
        if dataset_path:
            self._participants_tab.refresh_table(dataset_path)

        # Update the subject dropdown (Import Files tab)
        self._import_files_tab.refresh_subject_dropdown()

    # --------------------------------------------------------------------- #
    # File-tree browser + BIDS validator (left-pane window chrome)
    # --------------------------------------------------------------------- #

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

        # //==[Ui Layout]
        self.fileTreeView.setAnimated(False)
        self.fileTreeView.setIndentation(20)
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

        # Use the PatientTableController (owned by the Participants tab) to rename
        subject_controller = self._participants_tab.subject_controller
        if subject_controller:
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
            success = subject_controller.update_subject_field(
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

        # Perform deletions using the PatientTableController (owned by the tab)
        subject_controller = self._participants_tab.subject_controller
        if not subject_controller:
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
            success = subject_controller.delete_subject(subject_id)

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

    # --------------------------------------------------------------------- #
    # menu / dataset chrome
    # --------------------------------------------------------------------- #

    def open_db_options(self):
        self.__optionWindow = OptionWindow()
        self.__optionWindow.show()

    def show_about_dialog(self):
        """Show the About dialog."""
        about_dialog = AboutDialog(self)
        about_dialog.exec()

    def create_dataset(self):
        """Create a new BIDS dataset: gather inputs here, then delegate to the controller."""
        default_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DesktopLocation
        )
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select a folder to save the BIDS dataset", default_dir
        )
        if not folder_path:
            return  # user cancelled folder selection

        dataset_name, ok = QInputDialog.getText(
            self, "Dataset Name", "Enter a name for the dataset"
        )
        if not ok:
            return  # user cancelled the name prompt

        # An empty (but confirmed) name is reported back via operation_failed.
        self._main_controller.create_dataset(folder_path, dataset_name)

    def open_dataset(self):
        """Open an existing BIDS dataset: gather the folder here, then delegate to the controller."""
        default_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DesktopLocation
        )
        folder_path = QFileDialog.getExistingDirectory(self, "Select a folder", default_dir)
        if not folder_path:
            return  # user cancelled
        self._main_controller.open_dataset(folder_path)

    def _on_dataset_operation_failed(self, title: str, message: str):
        """Show an error/warning for a failed dataset operation (from DatasetController)."""
        # A dataset error can arrive while the validation progress dialog is open.
        self._close_validation_progress_dialog()
        QMessageBox.warning(self, title, message)

    def _on_validation_started(self, message: str):
        """Open the validation progress dialog (DatasetController signalled a start)."""
        self._close_validation_progress_dialog()
        self._validation_progress_dialog = ValidationProgressDialog(self)
        self._validation_progress_dialog.show()
        self._validation_progress_dialog.set_status(message)

    def _on_validation_finished(self, validation_result):
        """Close the progress dialog and show the validation results dialog."""
        self._close_validation_progress_dialog()
        results_dialog = ValidationResultsDialog(self)
        results_dialog.display_validation_result(validation_result)
        results_dialog.exec()

    def _close_validation_progress_dialog(self):
        """Close and drop the validation progress dialog if it is open."""
        if self._validation_progress_dialog is not None:
            self._validation_progress_dialog.close()
            self._validation_progress_dialog = None

    def _update_validation_state(self):
        """Update validation state from the dataset model."""
        if hasattr(self, '_main_controller') and self._main_controller.is_dataset_loaded():
            dataset_model = self._main_controller.dataset_controller.model
            self._validation_level = dataset_model.validation_level
            self._validation_issues = dataset_model.validation_issues
            self._is_valid_bids_dataset = self._validation_level == "STRICT_BIDS"
        else:
            self._validation_level = "NOT_BIDS"
            self._validation_issues = []
            self._is_valid_bids_dataset = False

    def _show_validation_warning_if_needed(self):
        """Show validation warning dialog if dataset is not fully BIDS compliant."""
        if self._validation_level == "NOT_BIDS":
            issues_text = "\n".join(f"• {issue}" for issue in self._validation_issues)

            reply = QMessageBox.question(
                self,
                "Not a BIDS Dataset",
                f"This folder does not appear to be a valid BIDS dataset:\n\n"
                f"{issues_text}\n\n"
                f"Operations like renaming and deleting subjects/files will be restricted "
                f"to prevent data corruption.\n\n"
                f"Would you like to:\n"
                f"• Click 'Yes' to load anyway (view-only mode)\n"
                f"• Click 'No' to select a different folder",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                # Try to open a different dataset (view gathers the folder).
                self.open_dataset()

        elif self._validation_level == "PARTIAL_BIDS":
            issues_text = "\n".join(f"• {issue}" for issue in self._validation_issues)

            QMessageBox.warning(
                self,
                "Partial BIDS Dataset",
                f"This dataset has some BIDS structure but is missing required components:\n\n"
                f"{issues_text}\n\n"
                f"Some operations may be restricted. Consider fixing these issues "
                f"to enable full functionality."
            )

    def _update_tabs_based_on_validation(self):
        """Enable/disable tabs based on BIDS validation level."""
        if self._validation_level == "NOT_BIDS":
            # Disable entire tab widget for non-BIDS folders
            self.tabWidget.setEnabled(False)
        else:
            # Enable tab widget and all tabs for valid BIDS datasets
            self.tabWidget.setEnabled(True)
            self.tabWidget.setTabEnabled(0, True)   # Participants tab
            self.tabWidget.setTabEnabled(1, True)   # Import Files tab
            self.tabWidget.setTabEnabled(2, True)   # Import Subjects tab

    def refresh_validation_state(self):
        """Force refresh of validation state - can be called manually."""
        self._update_validation_state()
        self._update_tabs_based_on_validation()
