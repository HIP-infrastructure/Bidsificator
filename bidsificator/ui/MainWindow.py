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
from ..ui.OptionWindow import OptionWindow
from ..ui.StatusBarManager import StatusBarManager
from ..ui.tabs.import_files_tab import ImportFilesTab
from ..ui.tabs.import_subjects_tab import ImportSubjectsTab
from ..ui.tabs.participants_tab import ParticipantsTabMixin
from ..ui.ValidationResultsDialog import ValidationProgressDialog, ValidationResultsDialog

logger = logging.getLogger(__name__)


class MainWindow(
    QMainWindow,
    Ui_MainWindow,
    ParticipantsTabMixin,
):
    """Main application window.

    The Import Files and Import Subjects tabs are self-contained QWidgets
    (`ImportFilesTab`/`ImportSubjectsTab`, 9d.1–9d.2); only the Participants tab's
    slots still live in a mixin (see `bidsificator.ui.tabs`). This class owns
    window setup, the controller wiring, the cross-tab signal handlers, dataset
    create/open, the validation state, and the file-tree/validation chrome.
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

        # The Import Files (9d.2) and Import Subjects (9d.1) tabs are
        # self-contained QWidgets that own their widgets + behaviour and wire
        # their own controller signals. Built after the MainController exists
        # (they take it by injection) and inserted in ASCENDING index order after
        # the still-inline Participants tab — QTabWidget.insertTab clamps the
        # index to count(), so files (1) must precede subjects (2).
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
        # Cross-tab: a subject added/renamed/removed on the Participants tab must
        # refresh the Import Files subject dropdown.
        self.tableWidget.subject_updated.connect(self._import_files_tab.refresh_subject_dropdown)

        # Setup file tree context menu
        self.fileTreeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.fileTreeView.customContextMenuRequested.connect(self.show_file_tree_context_menu)

        # Enable multi-selection in file tree for subject operations
        self.fileTreeView.setSelectionMode(self.fileTreeView.SelectionMode.ExtendedSelection)

        #    The Import Files (second) and Import Subjects (third) tabs wire
        #    themselves inside their QWidget classes. The BIDS-validator button is
        #    window chrome (left pane), so it stays wired here.
        self.BidsValidatorPushButton.clicked.connect(self.validate_bids_dataset)

    def _get_dataset_path(self) -> str:
        """Get current dataset path for PatientTableWidget."""
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

        # The Import Files and Import Subjects tabs wire their own controller
        # signals inside their QWidget classes.

    def _on_dataset_changed(self, dataset_path: str):
        """Handle dataset change from controller."""
        # Update validation state and tabs
        self._update_validation_state()
        self.load_treeView_UI(dataset_path)
        self._update_tabs_based_on_validation()

        # Only load subjects and update UI if it's a valid dataset
        if self._validation_level != "NOT_BIDS":
            self.tableWidget.LoadSubjectsInTableWidget(dataset_path)
            self._import_files_tab.refresh_subject_dropdown()

        # Show validation warning if necessary
        self._show_validation_warning_if_needed()

    def _on_subjects_updated(self):
        """Handle subjects update from controller - refreshes both table and dropdown."""
        # Update the subject table (first tab)
        dataset_path = self._get_dataset_path()
        if dataset_path:
            self.tableWidget.LoadSubjectsInTableWidget(dataset_path)

        # Update the subject dropdown (Import Files tab)
        self._import_files_tab.refresh_subject_dropdown()

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
