import logging

from PyQt6.QtCore import QStandardPaths, Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
)

from ..controllers.MainController import MainController
from ..forms.MainWindow_ui import Ui_MainWindow
from ..ui.AboutDialog import AboutDialog
from ..ui.FileEditor import FileEditor
from ..ui.OptionWindow import OptionWindow
from ..ui.StatusBarManager import StatusBarManager
from ..ui.tabs.import_files_tab import ImportFilesTabMixin
from ..ui.tabs.import_subjects_tab import ImportSubjectsTabMixin
from ..ui.tabs.participants_tab import ParticipantsTabMixin
from ..ui.ValidationResultsDialog import ValidationProgressDialog, ValidationResultsDialog

logger = logging.getLogger(__name__)


class MainWindow(
    QMainWindow,
    Ui_MainWindow,
    ParticipantsTabMixin,
    ImportFilesTabMixin,
    ImportSubjectsTabMixin,
):
    """Main application window.

    The per-tab slots and helpers live in the tab mixins (see
    `bidsificator.ui.tabs`); this class owns window setup, the controller
    wiring, the cross-tab signal handlers, dataset create/open, the validation
    state, and the status-bar handlers.
    """

    _browse_folder_path_memory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
    _import_subject_file_editor = None
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

        # Create FileEditor for Import Subjects tab
        self._import_subject_file_editor = FileEditor()
        self.IS_FileEditorLayout.addWidget(self._import_subject_file_editor)
        # Initialize Import Files tab. The file list, current subject, and contact
        # labeling file live in ImportFilesController/ImportSessionModel — the view
        # holds no parallel copy.
        self.setup_import_files_tab()

        # Populate modality dropdown with schema-driven values
        self.populate_modality_dropdown()

        # Make SessionComboBox editable for custom session names
        self._setup_session_combobox()

        # Initialize MVC Controller
        self._main_controller = MainController(self)
        self._setup_controller_connections()

        # Initialize PatientTableWidget controller
        self.tableWidget.initialize_controller(self._get_dataset_path)

        # Connect PatientTableWidget signals to MainController so it stays in sync
        self.tableWidget.subject_updated.connect(self._notify_main_controller_subjects_changed)

        # Connect Menu
        self.actionNew_Bids_Dataset.triggered.connect(self.create_dataset)
        self.actionOpen_Bids_Dataset.triggered.connect(self.open_dataset)
        self.actionDatabase_Configuration.triggered.connect(self.open_db_options)
        self.actionAbout.triggered.connect(self.show_about_dialog)

        # Connect UI
        #    First tab
        self.CreateSubjectPushButton.clicked.connect(self.create_subject)
        self.SubjectLineEdit.setCursorPosition(len(self.SubjectLineEdit.text()))
        self.tableWidget.subject_updated.connect(self.update_subject_names_dropDown)

        # Setup file tree context menu
        self.fileTreeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.fileTreeView.customContextMenuRequested.connect(self.show_file_tree_context_menu)

        # Enable multi-selection in file tree for subject operations
        self.fileTreeView.setSelectionMode(self.fileTreeView.SelectionMode.ExtendedSelection)

        #    Second tab
        #       Add/Remove file
        self.ModalityComboBox.currentIndexChanged.connect(self.update_modality_UI)
        # Browse button removed from UI - files selected via "+" button only
        # Make path field read-only for information display
        self.BrowseLineEdit.setReadOnly(True)
        self.TaskComboBox.currentTextChanged.connect(self.update_task_combobox_UI)
        self.AddFileButton.clicked.connect(self.add_multiple_files)
        self.RemoveFileButton.clicked.connect(self.remove_file_from_list)
        # Import File List Widget connections
        self.ImportFileListWidget.itemClicked.connect(self.on_import_file_selected)
        self.ImportFileListWidget.itemSelectionChanged.connect(self.on_import_file_selected)
        # Clinical electrode labeling file connection
        self.ClinicalElecPushButton.clicked.connect(self.browse_clinical_electrode_file)
        self.ClinicalElecLineEdit.setReadOnly(True)  # Make read-only like BrowseLineEdit
        #    Third tab
        self.IS_ParsePushButton.clicked.connect(self.parse_subject_to_import)
        self.IS_SubjectListWidget.itemClicked.connect(self.update_import_subject_fileList)
        self.IS_SubjectListWidget.itemSelectionChanged.connect(self.update_import_subject_fileList)
        self.IS_StartImportPushButton.clicked.connect(self.start_subjects_import)
        self.IS_SubjectListWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.IS_SubjectListWidget.customContextMenuRequested.connect(self.show_delete_import_subject_context_menu)
        # Lookup table connections
        self.CreateLutPushButton.clicked.connect(self.create_lookup_template)
        self.BrowseLutPushButton.clicked.connect(self.browse_lookup_table)
        self.lineEdit.textChanged.connect(self.on_lookup_table_path_changed)
        #    Buttons
        self.StartImportPushButton.clicked.connect(self.start_file_import)
        self.BidsValidatorPushButton.clicked.connect(self.validate_bids_dataset)

        # Trigger UI for the first time
        self.progressBar.setValue(0)  # Second tab progress bar
        self.IS_progressBar.setValue(0)  # Third tab progress bar
        self.update_modality_UI()

    def _get_dataset_path(self) -> str:
        """Get current dataset path for PatientTableWidget."""
        if hasattr(self, '_main_controller') and self._main_controller:
            return self._main_controller.dataset_controller.dataset_path
        return ""

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

        # Import files controller signals (Second tab)
        import_files_ctrl = self._main_controller.import_files_controller
        # Cache the controller: it is the single source of truth for this tab.
        self._import_files_controller = import_files_ctrl
        import_files_ctrl.file_list_changed.connect(self.refresh_import_file_list)
        import_files_ctrl.form_data_updated.connect(self._update_form_from_data)
        import_files_ctrl.progress_updated.connect(self.progressBar.setValue)  # Second tab progress bar
        import_files_ctrl.progress_updated.connect(self._on_file_import_progress)
        import_files_ctrl.import_completed.connect(self._on_file_import_completed)
        import_files_ctrl.import_failed.connect(self._on_import_failed)
        import_files_ctrl.import_failed.connect(self._show_file_import_failed_dialog)
        import_files_ctrl.operation_failed.connect(self._on_operation_failed)
        import_files_ctrl.dialog_dismissed.connect(self._on_dialog_dismissed)

        # Import subjects controller signals (Third tab)
        import_subjects_ctrl = self._main_controller.import_subjects_controller
        import_subjects_ctrl.subjects_loaded.connect(self._on_subjects_loaded)
        import_subjects_ctrl.selection_changed.connect(self._on_import_subject_selection_changed)
        import_subjects_ctrl.progress_updated.connect(self.IS_progressBar.setValue)  # Third tab progress bar
        import_subjects_ctrl.progress_updated.connect(self._on_subjects_import_progress)
        import_subjects_ctrl.import_completed.connect(self._on_subjects_import_completed)
        import_subjects_ctrl.import_failed.connect(self._on_import_failed)
        import_subjects_ctrl.dialog_dismissed.connect(self._on_dialog_dismissed)
        import_subjects_ctrl.lookup_table_updated.connect(self._on_lookup_table_updated)

    def _on_dataset_changed(self, dataset_path: str):
        """Handle dataset change from controller."""
        # Update validation state and tabs
        self._update_validation_state()
        self.load_treeView_UI(dataset_path)
        self._update_tabs_based_on_validation()

        # Only load subjects and update UI if it's a valid dataset
        if self._validation_level != "NOT_BIDS":
            self.tableWidget.LoadSubjectsInTableWidget(dataset_path)
            self.update_subject_names_dropDown()

        # Show validation warning if necessary
        self._show_validation_warning_if_needed()

    def _on_subjects_updated(self):
        """Handle subjects update from controller - refreshes both table and dropdown."""
        # Update the subject table (first tab)
        dataset_path = self._get_dataset_path()
        if dataset_path:
            self.tableWidget.LoadSubjectsInTableWidget(dataset_path)

        # Update the subject dropdown (second tab)
        self.update_subject_names_dropDown()

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
            self.tabWidget.setTabEnabled(0, True)   # Dataset/subjects tab
            self.tabWidget.setTabEnabled(1, True)   # Import Files tab
            self.tabWidget.setTabEnabled(2, True)   # Import Subjects tab

    def refresh_validation_state(self):
        """Force refresh of validation state - can be called manually."""
        self._update_validation_state()
        self._update_tabs_based_on_validation()

    # Status bar handler methods

    def _on_file_import_progress(self, progress: int):
        """Handle file import progress update for status bar."""
        self._status_bar_manager.show_progress("Importing files...", progress)

    def _on_file_import_completed(self, results: dict):
        """Handle file import completion: status bar + completion dialog."""
        file_count = results.get("files_imported", 0)
        self._status_bar_manager.show_success(f"Successfully imported {file_count} files")
        QMessageBox.information(
            self,
            "Import Complete",
            f"Successfully imported {file_count} files.\n\n"
            "Files remain in the list for review. You can:\n"
            "• Check/modify any file settings\n"
            "• Remove files if needed\n"
            "• Add more files\n"
            "• Re-import if there were issues",
        )

    def _show_file_import_failed_dialog(self, message: str):
        """Render a file-import failure (from ImportFilesController) as a modal."""
        QMessageBox.critical(
            self,
            "Import Failed",
            f"The file import did not complete:\n\n{message}",
        )

    def _on_operation_failed(self, title: str, message: str):
        """Render a controller-reported failure (warning) from the import tabs."""
        QMessageBox.warning(self, title, message)

    def _on_subjects_import_progress(self, progress: int):
        """Handle subjects import progress update for status bar."""
        self._status_bar_manager.show_progress("Importing subjects...", progress)

    def _on_subjects_import_completed(self, results: dict):
        """Handle subjects import completion for status bar."""
        subject_count = results.get("subjects_imported", 0)
        file_count = results.get("total_files", 0)
        self._status_bar_manager.show_success(
            f"Successfully imported {subject_count} subjects ({file_count} files)"
        )

    def _on_import_failed(self, error_message: str):
        """Handle import failure for status bar."""
        self._status_bar_manager.show_error(f"Import failed: {error_message}")

    def _on_dialog_dismissed(self):
        """Handle dialog dismissal - clear status bar."""
        self._status_bar_manager.clear()
