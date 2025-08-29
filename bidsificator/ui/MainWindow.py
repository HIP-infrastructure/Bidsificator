import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QMenu,
)
from PyQt6.QtCore import Qt, QStandardPaths
from PyQt6.QtGui import QFileSystemModel, QCursor

from bidsificator.workers import ImportBidsSubjectsWorker

from ..core.BidsFolder import BidsFolder
from ..core.BidsUtilityFunctions import BidsUtilityFunctions
from ..core.DataCrawler import DataCrawler
from ..forms.MainWindow_ui import Ui_MainWindow
from ..workers.ImportBidsFilesWorker import ImportBidsFilesWorker
from ..workers.ImportBidsSubjectsWorker import ImportBidsSubjectsWorker
from ..ui.FileEditor import FileEditor
from ..ui.OptionWindow import OptionWindow
from ..services.FileDetectionService import FileDetectionService
from ..services.ImportService import ImportService
from ..services.ValidationService import ValidationService
from ..services.DataCrawlerService import DataCrawlerService
from ..controllers.MainController import MainController

class MainWindow(QMainWindow, Ui_MainWindow):
    __subject_data = []
    __worker = None
    __browse_folder_path_memory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
    __ImportSubjectFileEditor = None
    __import_files_data = None  # Store files to import for current subject
    __optionWindow = None

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        # Set up splitter with reasonable default sizes
        # 25% for file tree, 75% for main content
        self.mainSplitter.setSizes([300, 700])

        # Create FileEditor for Import Subjects tab
        self.__ImportSubjectFileEditor = FileEditor()
        self.IS_FileEditorLayout.addWidget(self.__ImportSubjectFileEditor)
        # Initialize Import Files tab
        self.__import_files_data = {"subject_id": "", "files": []}
        self.setup_import_files_tab()
        
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

        # Connect UI
        #    First tab
        self.CreateSubjectPushButton.clicked.connect(self.create_subject)
        self.SubjectLineEdit.setCursorPosition(len(self.SubjectLineEdit.text()))
        self.tableWidget.subject_updated.connect(self.update_subject_names_dropDown)

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
        #    Third tab
        self.IS_ParsePushButton.clicked.connect(self.parse_subject_to_import)
        self.IS_SubjectListWidget.itemClicked.connect(self.update_import_subject_fileList)
        self.IS_SubjectListWidget.itemSelectionChanged.connect(self.update_import_subject_fileList)
        self.IS_StartImportPushButton.clicked.connect(self.start_subjects_import)
        self.IS_SubjectListWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.IS_SubjectListWidget.customContextMenuRequested.connect(self.show_delete_import_subject_context_menu)
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
        self._main_controller.subjects_updated.connect(self.update_subject_names_dropDown)
        
        # Import files controller signals (Second tab)
        import_files_ctrl = self._main_controller.import_files_controller
        import_files_ctrl.file_list_changed.connect(self.refresh_import_file_list)
        import_files_ctrl.selection_changed.connect(self._on_import_file_selection_changed)
        import_files_ctrl.form_data_updated.connect(self._update_form_from_data)
        import_files_ctrl.progress_updated.connect(self.progressBar.setValue)  # Second tab progress bar
        
        # Import subjects controller signals (Third tab)
        import_subjects_ctrl = self._main_controller.import_subjects_controller
        import_subjects_ctrl.subjects_loaded.connect(self._on_subjects_loaded)
        import_subjects_ctrl.selection_changed.connect(self._on_import_subject_selection_changed)
        import_subjects_ctrl.progress_updated.connect(self.IS_progressBar.setValue)  # Third tab progress bar
        
    def _on_dataset_changed(self, dataset_path: str):
        """Handle dataset change from controller."""
        self.load_treeView_UI(dataset_path)
        self.tabWidget.setEnabled(True)  # Enable tabs when dataset is loaded
        
        # Load subjects into the PatientTableWidget
        self.tableWidget.LoadSubjectsInTableWidget(dataset_path)
        self.update_subject_names_dropDown()
        
    def _on_import_file_selection_changed(self, index: int):
        """Handle import file selection change from controller."""
        self.__current_selected_file_index = index
        
    def _update_form_from_data(self, form_data: dict):
        """Update form fields from controller data."""
        if form_data:
            self.BrowseLineEdit.setText(form_data.get("file_path", "No file selected"))
            self.set_comboBox_text(self.ModalityComboBox, form_data.get("modality", ""))
            self.set_comboBox_text(self.SessionComboBox, form_data.get("session", ""))
            self.set_comboBox_text(self.TaskComboBox, form_data.get("task", ""))
            self.ContrastAgentLineEdit.setText(form_data.get("contrast_agent", ""))
            self.AcquisitionLineEdit.setText(form_data.get("acquisition", ""))
            self.ReconstructionLineEdit.setText(form_data.get("reconstruction", ""))
            
    def _on_subjects_loaded(self):
        """Handle subjects loaded from import subjects controller."""
        self.IS_SubjectListWidget.clear()
        subject_ids = self._main_controller.import_subjects_controller.get_subject_ids()
        for subject_id in subject_ids:
            self.IS_SubjectListWidget.addItem(subject_id)
            
    def _on_import_subject_selection_changed(self, index: int):
        """Handle import subject selection change from controller."""
        # This will be handled by the controller updating the file editor
        pass

    def open_db_options(self):
        self.__optionWindow = OptionWindow()
        self.__optionWindow.show()

    def create_dataset(self):
        """Create a new BIDS dataset using the controller."""
        self._main_controller.create_dataset()

    def open_dataset(self):
        """Open an existing BIDS dataset using the controller."""
        self._main_controller.open_dataset()

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
        """Handle subject selection change in Import Files tab"""
        current_subject = self.SubjectComboBox.currentText()
        
        # If no files, just update subject
        if not self.__import_files_data["files"]:
            self.__import_files_data["subject_id"] = current_subject
            return
        
        # If subject actually changed and there are files, prompt user
        if self.__import_files_data["subject_id"] != current_subject:
            # Prevent recursive calls when reverting subject
            if hasattr(self, '_reverting_subject') and self._reverting_subject:
                return
                
            reply = QMessageBox.question(
                self,
                "Subject Changed",
                f"You're switching from '{self.__import_files_data['subject_id']}' to '{current_subject}'.\n\n"
                f"What would you like to do with the {len(self.__import_files_data['files'])} files in the list?\n\n"
                f"• YES: Update all files to use '{current_subject}'\n"
                f"• NO: Cancel - keep '{self.__import_files_data['subject_id']}' selected",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes  # Default to updating files
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Update all existing files to use new subject
                for file_data in self.__import_files_data["files"]:
                    file_data["intended_subject"] = current_subject
                self.__import_files_data["subject_id"] = current_subject
            else:
                # Cancel - revert to original subject selection
                self._reverting_subject = True
                self.set_comboBox_text(self.SubjectComboBox, self.__import_files_data["subject_id"])
                self._reverting_subject = False
                # Keep everything as it was
        else:
            # Same subject, just update
            self.__import_files_data["subject_id"] = current_subject
            
    def setup_import_files_tab(self):
        """Initialize the Import Files tab"""
        # Set up the list widget for displaying files
        self.ImportFileListWidget.setSelectionMode(self.ImportFileListWidget.SelectionMode.SingleSelection)
        # Track the currently selected file index for form persistence
        self.__current_selected_file_index = -1
        # Initially disable form elements since no files are loaded
        self.set_import_form_enabled(False)
        
    def save_current_form_to_data(self):
        """Save current form fields to the currently selected file's data"""
        if self.__current_selected_file_index >= 0 and self.__current_selected_file_index < len(self.__import_files_data["files"]):
            file_data = self.__import_files_data["files"][self.__current_selected_file_index]
            
            # Update the stored data with current form values
            file_data["modality"] = self.ModalityComboBox.currentText()
            file_data["session"] = self.SessionComboBox.currentText().removeprefix("ses-") if self.SessionComboBox.currentText() else ""
            file_data["task"] = self.TaskComboBox.currentText()
            file_data["contrast_agent"] = self.ContrastAgentLineEdit.text()
            file_data["acquisition"] = self.AcquisitionLineEdit.text()
            file_data["reconstruction"] = self.ReconstructionLineEdit.text()

    def on_import_file_selected(self):
        """Update form fields when a file is selected in the list"""
        # Save current form data before switching
        self.save_current_form_to_data()
        
        # Use current row if no selection (e.g., when called manually)
        selected_items = self.ImportFileListWidget.selectedItems()
        if not selected_items:
            current_row = self.ImportFileListWidget.currentRow()
            if current_row >= 0 and current_row < len(self.__import_files_data["files"]):
                index = current_row
            else:
                self.__current_selected_file_index = -1
                # No file selected - disable form and clear fields only if no files exist
                if len(self.__import_files_data["files"]) == 0:
                    self.set_import_form_enabled(False)
                    self.clear_import_form_fields()
                return
        else:
            # Get the index of selected file
            index = self.ImportFileListWidget.row(selected_items[0])
        
        self.__current_selected_file_index = index
        
        if index >= 0 and index < len(self.__import_files_data["files"]):
            file_data = self.__import_files_data["files"][index]
            
            # Enable form elements when a file is selected
            self.set_import_form_enabled(True)
            
            # Update form fields with file metadata
            self.BrowseLineEdit.setText(file_data["file_path"])
            self.set_comboBox_text(self.ModalityComboBox, file_data["modality"])
            self.set_comboBox_text(self.SessionComboBox, "ses-" + file_data["session"] if file_data["session"] else "")
            self.set_comboBox_text(self.TaskComboBox, file_data["task"])
            self.ContrastAgentLineEdit.setText(file_data["contrast_agent"])
            self.AcquisitionLineEdit.setText(file_data["acquisition"])
            self.ReconstructionLineEdit.setText(file_data["reconstruction"])
        else:
            # Index out of bounds - disable form and clear fields
            self.__current_selected_file_index = -1
            self.set_import_form_enabled(False)
            self.clear_import_form_fields()
    
    def remove_file_from_list(self):
        """Remove selected file from the import list"""
        selected_items = self.ImportFileListWidget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a file to remove")
            return
            
        index = self.ImportFileListWidget.row(selected_items[0])
        if index >= 0 and index < len(self.__import_files_data["files"]):
            # Remove from data structure
            self.__import_files_data["files"].pop(index)
            # Remove from list widget
            self.ImportFileListWidget.takeItem(index)
            
            # Update selection and form fields
            self.update_selection_after_removal(index)

    def update_selection_after_removal(self, removed_index):
        """Update selection and form fields after removing an item"""
        total_items = self.ImportFileListWidget.count()
        
        if total_items == 0:
            # No items left - disable form and clear everything
            self.set_import_form_enabled(False)
            self.clear_import_form_fields()
            return
        
        # Determine which item to select next
        if removed_index >= total_items:
            # Removed the last item, select the new last item
            new_selection = total_items - 1
        else:
            # Select the item that took the removed item's place
            new_selection = removed_index
        
        # Set the new selection
        self.ImportFileListWidget.setCurrentRow(new_selection)
        
        # Update form fields with the newly selected item
        self.on_import_file_selected()

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
        
        # Remove file button (only enable if files exist)
        self.RemoveFileButton.setEnabled(enabled and len(self.__import_files_data["files"]) > 0)
        
        # Import button (only enable if files exist)
        self.StartImportPushButton.setEnabled(enabled and len(self.__import_files_data["files"]) > 0)

    def create_subject(self):
        """Create a new subject using the controller."""
        subject_name = self.SubjectLineEdit.text().strip()
        
        if not subject_name:
            return  # Don't create empty subjects
        
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
        self._main_controller.parse_subjects_to_import('bidsificator/config/config.yaml')
        # UI update will be handled by controller signal

    def update_import_subject_fileList(self):
        """Update import subject file list using controller data."""
        selectedIndexes = self.IS_SubjectListWidget.selectedIndexes()
        if len(selectedIndexes) > 0:
            subject_id = self.IS_SubjectListWidget.item(selectedIndexes[0].row()).text()
            
            # First, save current FileEditor data back to ImportSubjectsController
            self._sync_file_editor_to_import_controller()
            
            self.__ImportSubjectFileEditor.clear_file_list()
            
            # Get subject data from controller
            subject_data = self._main_controller.import_subjects_controller.get_subject_by_id(subject_id)
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
        
        # Sync import data with first available subject (or empty if no subjects)
        if subject_names and not self.__import_files_data["files"]:
            # Only update if no files exist to avoid unwanted changes
            self.__import_files_data["subject_id"] = subject_names[0]
            # Update controller as well
            self._main_controller.import_files_controller.current_subject = subject_names[0]
        elif not subject_names:
            self.__import_files_data["subject_id"] = ""
            self._main_controller.import_files_controller.current_subject = ""
        
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
        self.SessionComboBox.clear()
        self.SessionComboBox.addItems(session_names)

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
        reply = QMessageBox.question(self, "Remove Subject", "Are you sure you want to remove the selected subject(s)?", buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        selectedIndexes = self.IS_SubjectListWidget.selectedIndexes()
        for index in selectedIndexes[::-1]:
            self.IS_SubjectListWidget.takeItem(index.row())
            self.__subject_data.pop(index.row())

        self.__ImportSubjectFileEditor.clear_file_list()

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
        else:
            print("Error : [__UpdateModalityUI] Modality not recognized")

    # Method removed - DICOM checkbox no longer exists in UI
    # def update_browseFile_UI(self, state):

    def is_dicom_folder(self, folder_path):
        """Check if a folder contains DICOM files"""
        return FileDetectionService.is_dicom_folder(folder_path)
    
    def browse_for_file_to_add(self):
        modality = self.ModalityComboBox.currentText()
        filters = FileDetectionService.get_file_filters()

        # For anatomy, allow both file and folder selection
        if "(anat)" in modality:
            # First try file selection
            file_filter = filters["(anat)"]
            file_path = QFileDialog.getOpenFileName(self, "Select a file (or Cancel to browse for DICOM folder)", 
                                                  self.__browse_folder_path_memory, filter=file_filter)
            if file_path[0]:
                self.__browse_folder_path_memory = os.path.dirname(file_path[0])
                self.BrowseLineEdit.setText(file_path[0])
            else:
                # User cancelled file selection, offer folder selection for DICOM
                reply = QMessageBox.question(self, "DICOM Folder?", 
                    "Do you want to select a DICOM folder instead?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    folder_path = QFileDialog.getExistingDirectory(self, "Select DICOM folder", 
                                                                 self.__browse_folder_path_memory)
                    if folder_path:
                        if self.is_dicom_folder(folder_path):
                            self.__browse_folder_path_memory = folder_path
                            self.BrowseLineEdit.setText(folder_path + " [DICOM Folder]")
                        else:
                            QMessageBox.warning(self, "Not a DICOM folder", 
                                "The selected folder doesn't appear to contain DICOM files.")
        elif any(key in modality for key in filters): # photo or ieeg file
            file_filter = next(filter for key, filter in filters.items() if key in modality)
            file_path = QFileDialog.getOpenFileName(self, "Select a file", self.__browse_folder_path_memory, filter=file_filter)
            if file_path[0]:
                self.__browse_folder_path_memory = os.path.dirname(file_path[0])
                self.BrowseLineEdit.setText(file_path[0])
        else:
            QMessageBox.warning(self, "Modality not recognized", "Please select a modality first")

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

    def add_file_to_list(self):
        #Need to validate focus for ui elements in order to get all the values
        self.TaskComboBox.clearFocus()
        self.SessionComboBox.clearFocus()
        self.ContrastAgentLineEdit.clearFocus()
        self.AcquisitionLineEdit.clearFocus()
        self.ReconstructionLineEdit.clearFocus()

        #Get file path and check if it's a DICOM folder
        file_path_raw = self.BrowseLineEdit.text()
        is_dicom_folder = "[DICOM Folder]" in file_path_raw
        file_path = file_path_raw.replace(" [DICOM Folder]", "") if is_dicom_folder else file_path_raw
        #Get file name (handle DICOM folders)
        if is_dicom_folder:
            file_name = f"{os.path.basename(file_path)} [DICOM Folder]"
        else:
            file_name = os.path.basename(file_path)
        #Get the modality
        modality = self.ModalityComboBox.currentText()
        #According to modality get the task and relevant elements from ui
        if "(anat)" in modality:
            task = ""
            session = self.SessionComboBox.currentText()
            contrast_agent = self.ContrastAgentLineEdit.text()
            acquisition = self.AcquisitionLineEdit.text()
            reconstruction = self.ReconstructionLineEdit.text()
        elif "ieeg (ieeg)" in modality:
            task = self.TaskComboBox.currentText()
            session = self.SessionComboBox.currentText()
            contrast_agent = ""
            acquisition = self.AcquisitionLineEdit.text()
            reconstruction = ""
        elif "photo (ieeg)" in modality:
            task = ""
            session = self.SessionComboBox.currentText()
            contrast_agent = ""
            acquisition = self.AcquisitionLineEdit.text()
            reconstruction = ""
        else:
            print("Error : [__AddFileToList] Modality not recognized")

        subject = {
            "subject_id": self.SubjectComboBox.currentText(),
            "files": [
                {
                "file_name": file_name,
                "file_path": file_path,
                "modality": modality,
                "task": task,
                "session": session.removeprefix("ses-"),
                "contrast_agent": contrast_agent,
                "acquisition": acquisition,
                "reconstruction": reconstruction
                }
            ]
        }

        # Check if file path is provided
        if not file_path:
            QMessageBox.warning(self, "No File", "Please browse for a file first")
            return
            
        # Check for duplicates
        for existing_file in self.__import_files_data["files"]:
            if existing_file["file_path"] == file_path:
                QMessageBox.warning(self, "Duplicate File", "This file is already in the list")
                return
        
        # Files added to currently selected subject
        current_subject = self.SubjectComboBox.currentText()
        self.__import_files_data["subject_id"] = current_subject
        
        # Add file to data structure
        file_data = {
            "file_name": file_name,
            "file_path": file_path,
            "modality": modality,
            "task": task,
            "session": session.removeprefix("ses-") if session else "",
            "contrast_agent": contrast_agent,
            "acquisition": acquisition,
            "reconstruction": reconstruction
        }
        self.__import_files_data["files"].append(file_data)
        
        # Add to list widget with simple filename display
        self.ImportFileListWidget.addItem(file_name)
        
        # Clear browse field for next file
        self.BrowseLineEdit.clear()

    def detect_modality_from_file(self, file_path):
        """Auto-detect modality from filename and extension"""
        return FileDetectionService.detect_modality_from_file(file_path)

    def get_next_acquisition_number(self, subject_id, session, modality, task):
        """Auto-increment acquisition for files with same properties"""
        return ImportService.get_next_acquisition_number(
            self.__import_files_data["files"], session, modality, task
        )

    def add_multiple_files(self):
        """Add multiple files using the controller."""
        
        try:
            # Always show all supported files for auto-detection
            file_filter = "All supported files (*.nii *.nii.gz *.trc *.vhdr *.edf *.png *.jpg *.tif)"
            
            # Open file dialog
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select files to import", 
                self.__browse_folder_path_memory,
                file_filter
            )
            
            
            if not files:
                return
                
            # Update browse memory
            self.__browse_folder_path_memory = os.path.dirname(files[0])
        
            # Get form values
            current_subject = self.SubjectComboBox.currentText()
            session = self.SessionComboBox.currentText()
            task = self.TaskComboBox.currentText()
            contrast_agent = self.ContrastAgentLineEdit.text()
            acquisition = self.AcquisitionLineEdit.text()
            reconstruction = self.ReconstructionLineEdit.text()
            
            # Add each file
            successful_count = 0
            failed_files = []
            
            for file_path in files:
                file_name = os.path.basename(file_path)
                
                # Check for duplicates
                duplicate_found = False
                for existing_file in self.__import_files_data["files"]:
                    if existing_file["file_path"] == file_path:
                        failed_files.append(f"{file_name}: Already in list")
                        duplicate_found = True
                        break
                
                if duplicate_found:
                    continue
                
                # Auto-detect modality for this file
                detected_modality = self.detect_modality_from_file(file_path)
                if not detected_modality:
                    failed_files.append(f"{file_name}: Unsupported file type")
                    continue
                
                
                # Set task based on detected modality
                if "(anat)" in detected_modality or "photo" in detected_modality:
                    task_value = ""  # Anatomy and photos don't use tasks
                else:
                    task_value = task
                
                # Auto-increment acquisition number for files with same properties
                auto_acquisition = self.get_next_acquisition_number(
                    current_subject,
                    session.removeprefix("ses-") if session else "",
                    detected_modality,
                    task_value
                )
                
                    
                file_data = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "modality": detected_modality,
                    "task": task_value,
                    "session": session.removeprefix("ses-") if session else "",
                    "contrast_agent": contrast_agent if "(anat)" in detected_modality else "",
                    "acquisition": auto_acquisition,
                    "reconstruction": reconstruction if "(anat)" in detected_modality else "",
                    "intended_subject": current_subject
                }
                
                # Add to data structure
                self.__import_files_data["subject_id"] = current_subject
                self.__import_files_data["files"].append(file_data)
                successful_count += 1
            
            # Update UI
            self.refresh_import_file_list()
            
            # Show results
            if successful_count > 0 or failed_files:
                message = f"Successfully imported {successful_count} files"
                if failed_files:
                    message += f"\n\nFailed files:\n" + "\n".join(failed_files)
                
                QMessageBox.information(self, "Import Results", message)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to add files: {str(e)}")

    def add_file_to_import_data(self, file_data):
        """Add file to import data structure"""
        
        current_subject = self.SubjectComboBox.currentText()
        
        # Store the intended subject with each file
        file_data["intended_subject"] = current_subject
        
        # Check for duplicates
        for existing_file in self.__import_files_data["files"]:
            if existing_file["file_path"] == file_data["file_path"]:
                return False  # Skip duplicate
        
        # Add file
        self.__import_files_data["files"].append(file_data)
        return True

    def refresh_import_file_list(self):
        """Refresh the ImportFileListWidget display"""
        
        self.ImportFileListWidget.clear()
        
        for file_data in self.__import_files_data["files"]:
            # Show only filename - single subject tab
            display_text = file_data['file_name']
            self.ImportFileListWidget.addItem(display_text)
        
        # Auto-select first file if available
        if self.__import_files_data["files"]:
            self.ImportFileListWidget.setCurrentRow(0)
            self.__current_selected_file_index = 0
            # Enable form elements when files are present
            self.set_import_form_enabled(True)
            # Manually call file selection to populate form since setCurrentRow may not trigger signals
            self.on_import_file_selected()
        else:
            self.__current_selected_file_index = -1
            # Disable form elements when no files
            self.set_import_form_enabled(False)
            self.clear_import_form_fields()

    def browse_single_file_fallback(self):
        """Single-file browse as fallback option"""
        self.browse_for_file_to_add()

    def start_file_import(self):
        """Start file import using the controller."""
        # Save current form data before starting import
        self.save_current_form_to_data()
        
        
        # Reset progress bar for this tab
        self.progressBar.setValue(0)
        
        # Sync MainWindow data to controller before starting import
        self._sync_files_to_controller()
        
        # Use controller to start import
        self._main_controller.start_file_import()
    
    def _sync_files_to_controller(self):
        """Sync MainWindow file data to the controller."""
        if hasattr(self, '_main_controller') and self._main_controller:
            # Sync the current import data to the controller
            subject_id = self.__import_files_data["subject_id"]
            files = self.__import_files_data["files"]
            
            
            # Set the data in the controller
            self._main_controller.import_files_controller.set_files_data(subject_id, files)

    def start_subjects_import(self):
        """Start subjects import using the controller."""
        
        # Reset progress bar for this tab
        self.IS_progressBar.setValue(0)
        
        # Save any pending FileEditor changes before import
        self._save_file_editor_changes()
        
        self._main_controller.start_subjects_import()
    
    def _save_file_editor_changes(self):
        """Save FileEditor changes back to ImportSubjectsController."""
        # Make sure FileEditor saves its current form data
        if hasattr(self.__ImportSubjectFileEditor, '_save_form_data'):
            self.__ImportSubjectFileEditor._save_form_data()
        
        # Get the modified data from FileEditor controller
        if hasattr(self.__ImportSubjectFileEditor._controller, '_current_subject_data'):
            modified_data = self.__ImportSubjectFileEditor._controller._current_subject_data
            if modified_data:
                subject_id = modified_data.get("subject_id")
                # Here we would sync back to ImportSubjectsController, but for now the change persistence
                # in FileEditor should handle most of the persistence within the current subject

    def validate_bids_dataset(self):
        """Validate BIDS dataset using the controller."""
        subject_name = self.SubjectComboBox.currentText()
        self._main_controller.validate_bids_dataset(subject_name)

    def set_comboBox_text(self, comboBox, text):
        index = comboBox.findText(text)
        if index >= 0:
            comboBox.setCurrentIndex(index)
        else:
            comboBox.setCurrentIndex(-1)

        comboBox.clearFocus()

    def on_worker_finished(self):
        """Display a completion message and handle cleanup after the worker thread finishess"""

        print("File import finished")
        print("Updating Subjects list in the user interface")
        self.tableWidget.LoadSubjectsInTableWidget(self.fileTreeView.model().rootDirectory().path())
        self.update_subject_names_dropDown()
        
        # Check which type of worker finished to show appropriate message
        if isinstance(self.__worker, ImportBidsSubjectsWorker):
            # Count total files from all subjects
            total_files = sum(len(subject.get("files", [])) for subject in self.__subject_data)
            subject_count = len(self.__subject_data)
            QMessageBox.information(
                self, 
                "Import Complete", 
                f"Successfully imported {subject_count} subjects with {total_files} files.\n\n"
                "Check the dataset folder for the imported files."
            )
        else:
            # Import Files worker (single subject)
            file_count = len(self.__import_files_data["files"])
            QMessageBox.information(
                self, 
                "Import Complete", 
                f"Successfully imported {file_count} files.\n\n"
                "Files remain in the list for review. You can:\n"
                "• Check/modify any file settings\n" 
                "• Remove files if needed\n"
                "• Add more files\n"
                "• Re-import if there were issues"
            )
        
        print("Cleaning up worker")
        self.__worker.deleteLater()  # Clean up the worker thread
