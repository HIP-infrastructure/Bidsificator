import logging
import os
from pathlib import Path

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
from ..core.BidsUtilityFunctions import BidsUtilityFunctions
from ..forms.MainWindow_ui import Ui_MainWindow
from ..services.ValidationServiceSchema import ValidationService
from ..ui.AboutDialog import AboutDialog
from ..ui.FileEditor import FileEditor
from ..ui.OptionWindow import OptionWindow
from ..ui.StatusBarManager import StatusBarManager
from ..ui.ValidationResultsDialog import ValidationProgressDialog, ValidationResultsDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow, Ui_MainWindow):
    __browse_folder_path_memory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
    __ImportSubjectFileEditor = None
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
        self.__ImportSubjectFileEditor = FileEditor()
        self.IS_FileEditorLayout.addWidget(self.__ImportSubjectFileEditor)
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

    def _update_form_from_data(self, form_data: dict):
        """Populate the import form widgets from a model form-data dict.

        Single place that writes the Import Files form. The session value arrives
        with its "ses-" prefix (or empty); _set_session_combobox_text keeps an empty
        session empty so a session-less file round-trips unchanged through
        save_current_form_to_data().
        """
        if not form_data:
            return
        self.set_import_form_enabled(True)
        self.BrowseLineEdit.setText(form_data.get("file_path", "No file selected"))
        self.set_comboBox_text(self.ModalityComboBox, form_data.get("modality", ""))
        self._set_session_combobox_text(form_data.get("session", ""))
        self.set_comboBox_text(self.TaskComboBox, form_data.get("task", ""))
        self.ContrastAgentLineEdit.setText(form_data.get("contrast_agent", ""))
        self.AcquisitionLineEdit.setText(form_data.get("acquisition", ""))
        self.ReconstructionLineEdit.setText(form_data.get("reconstruction", ""))

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
            self.__ImportSubjectFileEditor.clear_file_list()

    def _on_import_subject_selection_changed(self, index: int):
        """Handle import subject selection change from controller."""
        # This will be handled by the controller updating the file editor
        pass

    def _on_lookup_table_updated(self, message: str):
        """Handle lookup table update message from controller."""
        # Update status or provide visual feedback
        # For now, just update the statusbar or show in console
        logger.debug("Lookup table status: %s", message)

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

    def on_subject_changed(self):
        """Handle subject selection change in Import Files tab."""
        # Prevent recursive calls when reverting the combobox after a cancel
        if getattr(self, "_reverting_subject", False):
            return

        current_subject = self.SubjectComboBox.currentText()
        previous_subject = self._import_files_controller.current_subject

        # The controller owns the "apply to all queued files?" confirmation prompt
        # (and only prompts when files are present and the subject actually changes).
        changed = self._import_files_controller.change_subject(current_subject, ask_user=True)

        if changed:
            if previous_subject != current_subject:
                # Subject actually changed: the contact labeling file no longer applies
                self.ClinicalElecLineEdit.clear()
                self._import_files_controller.contact_labeling_file = None
        else:
            # User cancelled: revert the combobox to the previous subject
            self._reverting_subject = True
            self.set_comboBox_text(self.SubjectComboBox, previous_subject)
            self._reverting_subject = False

    def setup_import_files_tab(self):
        """Initialize the Import Files tab"""
        # Set up the list widget for displaying files
        self.ImportFileListWidget.setSelectionMode(self.ImportFileListWidget.SelectionMode.SingleSelection)
        # Initially disable form elements since no files are loaded
        self.set_import_form_enabled(False)

    def _setup_session_combobox(self):
        """
        Configure SessionComboBox for flexible session input.

        Makes the combobox editable to allow custom session names per BIDS spec.
        Provides default options with ses-post first (selected by default).
        """
        # Add default session options first (before making it editable)
        self.SessionComboBox.addItems(['ses-post', 'ses-pre'])

        # Set ses-post as current selection
        self.SessionComboBox.setCurrentIndex(0)

        # Make combobox editable to allow custom session names
        self.SessionComboBox.setEditable(True)

        # Set placeholder text to guide users
        self.SessionComboBox.setPlaceholderText("Type session name (e.g., baseline, month6, 01)")

    def populate_modality_dropdown(self):
        """Populate ModalityComboBox with available datatypes from schema"""
        try:
            from ..core.bids_constants import MODALITY_DISPLAY_MAPPING
            from ..services.FileDetectionServiceSchema import FileDetectionService

            # Clear existing items (both static ones from UI and any previous dynamic ones)
            self.ModalityComboBox.clear()

            # Get available datatypes from schema
            detection_service = FileDetectionService()
            available_datatypes = detection_service.get_all_datatypes()

            # Add items for available datatypes using the shared display labels.
            for datatype in sorted(available_datatypes):
                if datatype in MODALITY_DISPLAY_MAPPING:
                    for display_name, _suffix in MODALITY_DISPLAY_MAPPING[datatype]:
                        self.ModalityComboBox.addItem(display_name)

        except Exception:
            logger.warning("Could not populate modality dropdown from schema", exc_info=True)
            # Fallback to basic items if schema loading fails
            fallback_items = [
                "T1w (anat)",
                "T2w (anat)",
                "ieeg (ieeg)",
                "eeg (eeg)",
                "photo (ieeg)"
            ]
            for item in fallback_items:
                self.ModalityComboBox.addItem(item)

    def _set_session_combobox_text(self, text):
        """Display `text` in the editable SessionComboBox, even when it is not an item.

        Custom session names (typed by the user) are not always in the item list,
        and an empty text must clear the selection so session-less files
        round-trip unchanged through save_current_form_to_data().
        """
        index = self.SessionComboBox.findText(text)
        self.SessionComboBox.setCurrentIndex(index)
        if index < 0:
            self.SessionComboBox.setEditText(text)
        self.SessionComboBox.clearFocus()

    def save_current_form_to_data(self):
        """Save current form fields to the currently selected file in the model."""
        form_data = {
            "modality": self.ModalityComboBox.currentText(),
            "session": self.SessionComboBox.currentText(),
            "task": self.TaskComboBox.currentText(),
            "contrast_agent": self.ContrastAgentLineEdit.text(),
            "acquisition": self.AcquisitionLineEdit.text(),
            "reconstruction": self.ReconstructionLineEdit.text(),
        }
        # No-op when there is no selection; strips the "ses-" prefix internally.
        self._import_files_controller.update_selected_file_from_form(form_data)

    def _load_import_file_into_form(self, index: int):
        """Load a file's metadata into the import form without saving first.

        Used for programmatic selection (refresh/rebuild) where the form may still
        show values from a previously selected file. Saving first would corrupt
        acquisitions (e.g. write acq-02 onto files[0]).
        """
        model = self._import_files_controller.model
        if model.file_model.get_file(index) is None:
            model.selected_file_index = -1
            self.set_import_form_enabled(False)
            self.clear_import_form_fields()
            return

        # Set the model selection directly (the model setter emits no signal) so the
        # form save/load timing stays under the view's control, then populate.
        model.selected_file_index = index
        self._update_form_from_data(model.get_form_data_for_selected_file())

    def on_import_file_selected(self):
        """Update form fields when a file is selected in the list (user-driven)."""
        # Save current form data before switching — only safe for user selection
        # when the form matches the model's current selection.
        self.save_current_form_to_data()

        model = self._import_files_controller.model

        # Use current row if no selection (e.g., when called manually)
        selected_items = self.ImportFileListWidget.selectedItems()
        if not selected_items:
            current_row = self.ImportFileListWidget.currentRow()
            if 0 <= current_row < self._import_files_controller.file_count:
                index = current_row
            else:
                model.selected_file_index = -1
                # No file selected - disable form and clear fields only if no files exist
                if self._import_files_controller.file_count == 0:
                    self.set_import_form_enabled(False)
                    self.clear_import_form_fields()
                return
        else:
            # Get the index of selected file
            index = self.ImportFileListWidget.row(selected_items[0])

        self._load_import_file_into_form(index)

    def remove_file_from_list(self):
        """Remove the selected file from the import list via the controller."""
        selected_items = self.ImportFileListWidget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a file to remove")
            return

        index = self.ImportFileListWidget.row(selected_items[0])
        # Point the model at the clicked row, then let the controller remove it. The
        # controller re-indexes the selection and emits file_list_changed, which
        # refresh_import_file_list turns into the rebuilt widget + reloaded form.
        self._import_files_controller.model.selected_file_index = index
        self._import_files_controller.remove_selected_file()

    def clear_import_form_fields(self):
        """Clear all import form fields"""
        self.BrowseLineEdit.setText("No file selected")
        self.ContrastAgentLineEdit.clear()
        self.AcquisitionLineEdit.clear()
        self.ReconstructionLineEdit.clear()

    def set_import_form_enabled(self, enabled):
        """Enable or disable import form elements"""
        # Form input elements
        self.ModalityComboBox.setEnabled(enabled)
        self.TaskComboBox.setEnabled(enabled)
        self.SessionComboBox.setEnabled(enabled)
        self.ContrastAgentLineEdit.setEnabled(enabled)
        self.AcquisitionLineEdit.setEnabled(enabled)
        self.ReconstructionLineEdit.setEnabled(enabled)

        # Remove/Import buttons only make sense when files are present. Guard the
        # controller lookup: this runs once during setup_import_files_tab(), before
        # the controller is created.
        has_files = (hasattr(self, "_import_files_controller")
                     and self._import_files_controller.file_count > 0)
        self.RemoveFileButton.setEnabled(enabled and has_files)
        self.StartImportPushButton.setEnabled(enabled and has_files)

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
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Create Subject Failed", error)

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

            self.__ImportSubjectFileEditor.clear_file_list()

            # Get subject data from controller using row index
            subject_data = self._main_controller.import_subjects_controller.model.get_subject(selected_row)
            if subject_data:
                # Convert dataclass to dictionary for FileEditor
                from dataclasses import asdict
                legacy_format = asdict(subject_data)
                self.__ImportSubjectFileEditor.add_files_to_list(legacy_format)

    def _sync_file_editor_to_import_controller(self):
        """Sync FileEditor changes back to ImportSubjectsController."""
        # Save any pending form changes first
        if hasattr(self.__ImportSubjectFileEditor, '_save_form_data'):
            self.__ImportSubjectFileEditor._save_form_data()

        # Get the current subject data from FileEditor controller
        if (hasattr(self.__ImportSubjectFileEditor, '_controller') and
            hasattr(self.__ImportSubjectFileEditor._controller, '_current_subject_data')):

            modified_data = self.__ImportSubjectFileEditor._controller._current_subject_data
            if modified_data and modified_data.get("subject_id"):
                subject_id = modified_data.get("subject_id")

                # Update the ImportSubjectsController with modified data
                self._main_controller.import_subjects_controller.update_subject_data(subject_id, modified_data)

    def update_subject_names_dropDown(self):
        """Update subject dropdown using controller data."""
        if not self._main_controller.is_dataset_loaded():
            return

        subject_names = self._main_controller.get_current_subjects()

        # Temporarily disconnect signals to prevent unwanted dialogs during update
        try:
            self.SubjectComboBox.currentTextChanged.disconnect(self.update_subject_details)
        except TypeError:
            pass  # Connection doesn't exist
        try:
            self.SubjectComboBox.currentTextChanged.disconnect(self.on_subject_changed)
        except TypeError:
            pass  # Connection doesn't exist

        self.SubjectComboBox.clear()
        self.SubjectComboBox.addItems(subject_names)

        # Sync the controller's current subject to the first available subject (or
        # empty if none), but only when no files are queued, to avoid silently
        # reassigning files the user already added.
        if subject_names and self._import_files_controller.file_count == 0:
            self._import_files_controller.current_subject = subject_names[0]
        elif not subject_names:
            self._import_files_controller.current_subject = ""

        # Reconnect signals after update is complete
        self.SubjectComboBox.currentTextChanged.connect(self.update_subject_details)
        self.SubjectComboBox.currentTextChanged.connect(self.on_subject_changed)

        # Populate session dropdown for the current subject
        if subject_names:
            self.update_subject_details()

    def update_subject_details(self):
        """Update subject details using controller data."""
        subject_name = self.SubjectComboBox.currentText()

        if not subject_name or not self._main_controller.is_dataset_loaded():
            return

        session_names = self._main_controller.get_sessions_for_subject(subject_name)

        # Clear and repopulate, but maintain editable functionality
        displayed_session = self.SessionComboBox.currentText()
        self.SessionComboBox.clear()

        # Add existing sessions from this subject
        if session_names:
            # Sort sessions to put ses-post first if it exists
            sorted_sessions = sorted(session_names, key=lambda x: (x != 'ses-post', x))
            self.SessionComboBox.addItems(sorted_sessions)
        else:
            # No sessions yet - add default with ses-post first
            self.SessionComboBox.addItems(['ses-post', 'ses-pre'])

        # Ensure combobox stays editable after repopulation
        if not self.SessionComboBox.isEditable():
            self.SessionComboBox.setEditable(True)
            self.SessionComboBox.setPlaceholderText("Type session name (e.g., baseline, month6, 01)")

        if self._import_files_controller.file_count > 0:
            # With files pending import, repopulating must not change the
            # displayed session: the next form save would stamp it onto the
            # selected file. This fires between two imports of the same list
            # (worker finished, subject switch), so restore what was shown.
            self._set_session_combobox_text(displayed_session)
        else:
            # No files yet: default to the first entry (ses-post when present).
            # An editable combobox does not auto-select after clear()+addItems,
            # so without this the session starts blank and newly added files
            # silently become session-less.
            self.SessionComboBox.setCurrentIndex(0)

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

    def update_modality_UI(self):
        if "(anat)" in self.ModalityComboBox.currentText():
            #session
            self.SessionLabel.show()
            self.SessionComboBox.show()
            #task - show for all modalities
            self.TaskLabel.show()
            self.TaskComboBox.show()
            #contrast
            self.ContrastAgentLabel.show()
            self.ContrastAgentLineEdit.show()
            #acquisition
            self.AcquisitionLabel.show()
            self.AcquisitionLineEdit.show()
            #reconstruction
            self.ReconstructionLabel.show()
            self.ReconstructionLineEdit.show()
            # Note: DICOM folder checkbox removed from UI
        elif "ieeg (ieeg)" in self.ModalityComboBox.currentText():
            #session
            self.SessionLabel.show()
            self.SessionComboBox.show()
            #task
            self.TaskLabel.show()
            self.TaskComboBox.show()
            #contrast
            self.ContrastAgentLabel.hide()
            self.ContrastAgentLineEdit.hide()
            #acquisition
            self.AcquisitionLabel.show()
            self.AcquisitionLineEdit.show()
            #reconstruction
            self.ReconstructionLabel.hide()
            self.ReconstructionLineEdit.hide()
            # Note: DICOM folder checkbox removed from UI
        elif "photo (ieeg)" in self.ModalityComboBox.currentText():
            #session
            self.SessionLabel.show()
            self.SessionComboBox.show()
            #task - show for all modalities
            self.TaskLabel.show()
            self.TaskComboBox.show()
            #contrast
            self.ContrastAgentLabel.hide()
            self.ContrastAgentLineEdit.hide()
            #acquisition
            self.AcquisitionLabel.show()
            self.AcquisitionLineEdit.show()
            #reconstruction
            self.ReconstructionLabel.hide()
            self.ReconstructionLineEdit.hide()
            # Note: DICOM folder checkbox removed from UI
        elif "eeg (eeg)" in self.ModalityComboBox.currentText():
            #session
            self.SessionLabel.show()
            self.SessionComboBox.show()
            #task
            self.TaskLabel.show()
            self.TaskComboBox.show()
            #contrast
            self.ContrastAgentLabel.hide()
            self.ContrastAgentLineEdit.hide()
            #acquisition
            self.AcquisitionLabel.show()
            self.AcquisitionLineEdit.show()
            #reconstruction
            self.ReconstructionLabel.hide()
            self.ReconstructionLineEdit.hide()
            # Note: DICOM folder checkbox removed from UI
        else:
            logger.warning("[__UpdateModalityUI] Modality not recognized")

    def update_task_combobox_UI(self):
        if "Other" in self.TaskComboBox.currentText():
            task_name = QInputDialog.getText(self, "Enter Task Name", "Enter a name for your task")[0]
            if task_name == "":
                QMessageBox.warning(self, "Dataset Name empty", "Please enter a valid name for your task")
                return
            else:
                self.TaskComboBox.currentTextChanged.disconnect(self.update_task_combobox_UI)
                #Insert the new task in TaskComboBox
                self.TaskComboBox.insertItem(self.TaskComboBox.count()-1, task_name)
                self.TaskComboBox.setCurrentIndex(self.TaskComboBox.count()-2)
                # Note: FileEditor TaskComboBox updates removed
                self.TaskComboBox.currentTextChanged.connect(self.update_task_combobox_UI)

    def add_multiple_files(self):
        """Add files to the import list via the controller (single source of truth)."""
        try:
            # Tag new files with the currently selected subject before adding.
            self._import_files_controller.current_subject = self.SubjectComboBox.currentText()
            # The controller opens the file dialog, runs schema-driven detection,
            # de-duplicates, auto-increments acquisitions, updates the model, and
            # shows the results dialog. Its file_list_changed signal drives
            # refresh_import_file_list to rebuild the widget.
            self._import_files_controller.add_multiple_files(
                self._get_current_form_values(),
                self.__browse_folder_path_memory,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add files: {str(e)}")

    def _get_current_form_values(self):
        """Get current form values for import."""
        return {
            'current_subject': self.SubjectComboBox.currentText(),
            'session': self.SessionComboBox.currentText(),
            'task': self.TaskComboBox.currentText(),
            'contrast_agent': self.ContrastAgentLineEdit.text(),
            'acquisition': self.AcquisitionLineEdit.text(),
            'reconstruction': self.ReconstructionLineEdit.text()
        }

    def refresh_import_file_list(self):
        """Rebuild the ImportFileListWidget from the model without corrupting metadata.

        Must not save the form before loading: after a rebuild the form may still
        show the previously selected file (e.g. acq-02), and writing that back would
        corrupt another file's acquisition. We only read from the model here.
        """
        self.ImportFileListWidget.blockSignals(True)
        try:
            self.ImportFileListWidget.clear()

            names = self._import_files_controller.get_file_names_for_list_widget()
            for display_text in names:
                # Show only filename - single subject tab
                self.ImportFileListWidget.addItem(display_text)

            if names:
                model = self._import_files_controller.model
                index = model.selected_file_index
                if not 0 <= index < len(names):
                    index = 0
                self.ImportFileListWidget.setCurrentRow(index)
                # Load form from the selected file without saving stale form values first
                self._load_import_file_into_form(index)
            else:
                self._import_files_controller.model.selected_file_index = -1
                self.set_import_form_enabled(False)
                self.clear_import_form_fields()
        finally:
            self.ImportFileListWidget.blockSignals(False)

    def browse_clinical_electrode_file(self):
        """Browse for clinical electrode labeling Excel file."""

        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Excel Files (*.xlsx *.xls)")
        file_dialog.setWindowTitle("Select Contact Labeling File")

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]

                # Validate file using ContactLabelingParser
                try:
                    from ..services.ContactLabelingParser import ContactLabelingParser
                    parser = ContactLabelingParser()
                    contact_data = parser.parse_file(Path(file_path))

                    # Show success message
                    contact_count = len(contact_data)
                    QMessageBox.information(
                        self,
                        "File Loaded",
                        f"Successfully loaded {contact_count} contacts from labeling file.\n\n"
                        f"File: {Path(file_path).name}"
                    )

                    # Update UI and store on the controller (single source of truth)
                    self.ClinicalElecLineEdit.setText(file_path)
                    self._import_files_controller.contact_labeling_file = file_path

                except FileNotFoundError as e:
                    QMessageBox.warning(
                        self,
                        "File Not Found",
                        f"The selected file could not be found:\n{str(e)}"
                    )
                except ValueError as e:
                    QMessageBox.warning(
                        self,
                        "Invalid File Format",
                        f"Could not parse Excel file:\n{str(e)}\n\n"
                        f"Please ensure the file has the correct structure with a 'contact' column."
                    )
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Error Loading File",
                        f"An unexpected error occurred:\n{str(e)}"
                    )

    def start_file_import(self):
        """Start file import using the controller."""
        # Save the current form to the selected file before importing
        self.save_current_form_to_data()

        # Reset progress bar for this tab
        self.progressBar.setValue(0)

        # Show starting message in status bar
        self._status_bar_manager.show_progress("File import in progress...")

        # The controller/model already hold the file list, current subject, and
        # contact labeling file (single source of truth) — no view->controller sync.
        self._main_controller.start_file_import()

    def start_subjects_import(self):
        """Start subjects import using the controller."""

        # Reset progress bar for this tab
        self.IS_progressBar.setValue(0)

        # Show starting message in status bar
        self._status_bar_manager.show_progress("Batch import in progress...")

        # Save any pending FileEditor changes before import
        self._save_file_editor_changes()

        # Get task value from the FileEditor's TaskComboBox
        task = self.__ImportSubjectFileEditor.TaskComboBox.currentText()

        self._main_controller.start_subjects_import(task)

    def _save_file_editor_changes(self):
        """Save FileEditor changes back to ImportSubjectsController."""
        # Force save of any pending form changes (even if user didn't click "Save")
        if hasattr(self.__ImportSubjectFileEditor, '_save_form_data'):
            self.__ImportSubjectFileEditor._save_form_data()

        # Also update any changed fields from the form directly
        if hasattr(self.__ImportSubjectFileEditor, '_save_form_data_to_controller'):
            self.__ImportSubjectFileEditor._save_form_data_to_controller()

        # Get the modified data from FileEditor controller and sync to ImportSubjectsController
        if (hasattr(self.__ImportSubjectFileEditor, '_controller')
                and hasattr(self.__ImportSubjectFileEditor._controller, '_current_subject_data')):
            modified_data = self.__ImportSubjectFileEditor._controller._current_subject_data
            if modified_data and modified_data.get("subject_id"):
                subject_id = modified_data.get("subject_id")
                # Sync changes back to ImportSubjectsController before import
                self._main_controller.import_subjects_controller.update_subject_data(subject_id, modified_data)

    def validate_bids_dataset(self):
        """Validate entire BIDS dataset using the controller."""
        # Validate the entire dataset, not just a single subject
        self._main_controller.validate_bids_dataset(subject_name=None)

    def set_comboBox_text(self, comboBox, text):
        index = comboBox.findText(text)
        if index >= 0:
            comboBox.setCurrentIndex(index)
        else:
            comboBox.setCurrentIndex(-1)

        comboBox.clearFocus()

    def browse_lookup_table(self):
        """Browse for CSV lookup table file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Lookup Table CSV File",
            self.__browse_folder_path_memory,
            "CSV files (*.csv *.txt);;All files (*.*)"
        )

        if file_path:
            self.__browse_folder_path_memory = os.path.dirname(file_path)
            self.lineEdit.setText(file_path)
            # The textChanged signal will trigger the controller update

    def on_lookup_table_path_changed(self, path: str):
        """Handle lookup table path change."""
        # Update controller when path changes
        self._main_controller.import_subjects_controller.set_lookup_table(path.strip())

    def create_lookup_template(self):
        """Create a lookup table template file."""
        self._main_controller.import_subjects_controller.create_lookup_template()

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
        """Handle file import completion for status bar."""
        file_count = results.get("files_imported", 0)
        self._status_bar_manager.show_success(f"Successfully imported {file_count} files")

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
