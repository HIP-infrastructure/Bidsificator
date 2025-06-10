import json
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
from bids_validator import BIDSValidator

from bidsificator.workers import ImportBidsSubjectsWorker

from ..core.BidsFolder import BidsFolder
from ..core.BidsUtilityFunctions import BidsUtilityFunctions
from ..core.DataCrawler import DataCrawler
from ..forms.MainWindow_ui import Ui_MainWindow
from ..workers.ImportBidsFilesWorker import ImportBidsFilesWorker
from ..workers.ImportBidsSubjectsWorker import ImportBidsSubjectsWorker
from ..ui.FileEditor import FileEditor
from ..ui.OptionWindow import OptionWindow

class MainWindow(QMainWindow, Ui_MainWindow):
    __subject_data = []
    __worker = None
    __browse_folder_path_memory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
    __ImportSubjectFileEditor = None
    __ImportFileFileEditor = None
    __optionWindow = None

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        # Create FileEditor
        self.__ImportSubjectFileEditor = FileEditor()
        self.IS_FileEditorLayout.addWidget(self.__ImportSubjectFileEditor)
        self.__ImportFileFileEditor = FileEditor()
        self.IF_FileEditorLayout.addWidget(self.__ImportFileFileEditor)

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
        self.AR_ModalityComboBox.currentIndexChanged.connect(self.update_modality_UI)
        self.AR_BrowsePushButton.clicked.connect(self.browse_for_file_to_add)
        self.AR_IsDicomFolderCheckBox.stateChanged.connect(self.update_browseFile_UI)
        self.AR_TaskComboBox.currentTextChanged.connect(self.update_task_combobox_UI)
        self.AR_AddPushButton.clicked.connect(self.add_file_to_list)
        self.AR_RemovePushButton.clicked.connect(self.__ImportFileFileEditor.remove_selected_file_from_list)
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
        self.progressBar.setValue(0)
        self.update_modality_UI()

    def open_db_options(self):
        self.__optionWindow = OptionWindow()
        self.__optionWindow.show()

    def create_dataset(self):
        folderPath = QFileDialog.getExistingDirectory(self, "Select a folder to save the BIDS dataset", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        if folderPath:
            dataset_name = QInputDialog.getText(self, "Dataset Name", "Enter a name for the dataset")[0]
            if dataset_name == "":
                QMessageBox.warning(self, "Dataset Name empty", "Please enter a dataset name")
                return

            # Clean the dataset name and create a unique path and update the dataset name
            dataset_path = folderPath + os.sep + BidsUtilityFunctions.clean_string(dataset_name)
            dataset_path = BidsUtilityFunctions.get_unique_path(dataset_path)
            dataset_name = os.path.basename(dataset_path).replace("_", " ")

            # Generate useful paths
            dataset_description_file_path = str(dataset_path) + os.sep +  "dataset_description.json"

            bids_folder = BidsFolder(dataset_path)
            bids_folder.create_folders()
            bids_folder.generate_empty_dataset_description_file(dataset_name, dataset_description_file_path)
            bids_folder.generate_participants_tsv()

            self.load_treeView_UI(dataset_path)
            self.tabWidget.setEnabled(True) # Enable the tabs only when a dataset is created
            self.tableWidget.LoadSubjectsInTableWidget(dataset_path)
            self.update_subject_names_dropDown()

    def open_dataset(self):
        folderPath = QFileDialog.getExistingDirectory(self, "Select a folder", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        if folderPath:
            self.load_treeView_UI(folderPath)
            self.tabWidget.setEnabled(True) # Enable the tabs only when a dataset is loaded
            self.tableWidget.LoadSubjectsInTableWidget(folderPath)
            self.update_subject_names_dropDown()

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

    def create_subject(self):
        if not self.fileTreeView.model():
            QMessageBox.warning(self, "No dataset selected", "Please open a BIDS dataset first")
            return

        subject_name = self.SubjectLineEdit.text()
        if not subject_name:
            QMessageBox.warning(self, "Subject Name empty", "Please enter a subject name")
            return

        if not subject_name.startswith("sub-"):
            QMessageBox.warning(self, "Subject Name not valid", "Subject name should start with 'sub-'")
            return

        self.tableWidget.CreateSubjectInTableWidget(subject_name)
        self.update_subject_names_dropDown()

    def parse_subject_to_import(self):
        self.__subject_data = DataCrawler.crawl_data('bidsificator/config/config.yaml')
        for subject in self.__subject_data:
            files = []
            for data_type, data_info in subject["data"].items():
                for file_path in data_info["file_paths"]:
                    file_name = Path(file_path).name
                    file = {
                        "file_name": file_name,
                        "file_path": file_path,
                        "modality": data_info['modality'],
                        "task": "",
                        "session": "post",
                        "contrast_agent": "",
                        "acquisition": "",
                        "reconstruction": ""
                    }
                    files.append(file)
            subject["files"] = files
            del subject["data"]

        self.IS_SubjectListWidget.clear()
        for subject in self.__subject_data:
            self.IS_SubjectListWidget.addItem(subject["subject_id"])

    def update_import_subject_fileList(self):
        selectedIndexes = self.IS_SubjectListWidget.selectedIndexes()
        if len(selectedIndexes) > 0:
            subject_id = self.IS_SubjectListWidget.item(selectedIndexes[0].row()).text()
            self.__ImportSubjectFileEditor.clear_file_list()
            for subject in self.__subject_data:
                if subject["subject_id"] == subject_id:
                    self.__ImportSubjectFileEditor.add_files_to_list(subject)
                    return

    def update_subject_names_dropDown(self):
        dataset_path = self.fileTreeView.model().rootDirectory().path()
        subject_names = [f for f in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, f)) and not f.startswith(".") and f.startswith("sub-")]

        self.AR_SubjectComboBox.currentTextChanged.connect(self.update_subject_details)
        self.AR_SubjectComboBox.clear()
        self.AR_SubjectComboBox.addItems(subject_names)

    def update_subject_details(self):
        dataset_path = self.fileTreeView.model().rootDirectory().path()
        subject_name = self.AR_SubjectComboBox.currentText()
        subject_path = os.path.join(dataset_path, subject_name)

        session_names = [f for f in os.listdir(subject_path) if os.path.isdir(os.path.join(subject_path, f)) and not f.startswith(".") and f.startswith("ses-")]
        self.AR_SessionComboBox.clear()
        self.AR_SessionComboBox.addItems(session_names)
        self.__ImportFileFileEditor.SessionComboBox.clear()
        self.__ImportFileFileEditor.SessionComboBox.addItems(session_names)

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
        if "(anat)" in self.AR_ModalityComboBox.currentText():
            #session
            self.AR_SessionLabel.show()
            self.AR_SessionComboBox.show()
            #task
            self.AR_TaskLabel.hide()
            self.AR_TaskComboBox.hide()
            #contrast
            self.AR_ContrastAgentLabel.show()
            self.AR_ContrastAgentLineEdit.show()
            #acquisition
            self.AR_AcquisitionLabel.show()
            self.AR_AcquisitionLineEdit.show()
            #reconstruction
            self.AR_ReconstructionLabel.show()
            self.AR_ReconstructionLineEdit.show()
            #deal with folder/file import
            self.AR_IsDicomFolderCheckBox.setEnabled(True)
        elif "ieeg (ieeg)" in self.AR_ModalityComboBox.currentText():
            #session
            self.AR_SessionLabel.show()
            self.AR_SessionComboBox.show()
            #task
            self.AR_TaskLabel.show()
            self.AR_TaskComboBox.show()
            #contrast
            self.AR_ContrastAgentLabel.hide()
            self.AR_ContrastAgentLineEdit.hide()
            #acquisition
            self.AR_AcquisitionLabel.show()
            self.AR_AcquisitionLineEdit.show()
            #reconstruction
            self.AR_ReconstructionLabel.hide()
            self.AR_ReconstructionLineEdit.hide()
            #deal with folder/file import
            self.AR_IsDicomFolderCheckBox.setChecked(False)
            self.AR_IsDicomFolderCheckBox.setEnabled(False)
        elif "photo (ieeg)" in self.AR_ModalityComboBox.currentText():
            #session
            self.AR_SessionLabel.show()
            self.AR_SessionComboBox.show()
            #task
            self.AR_TaskLabel.hide()
            self.AR_TaskComboBox.hide()
            #contrast
            self.AR_ContrastAgentLabel.hide()
            self.AR_ContrastAgentLineEdit.hide()
            #acquisition
            self.AR_AcquisitionLabel.show()
            self.AR_AcquisitionLineEdit.show()
            #reconstruction
            self.AR_ReconstructionLabel.hide()
            self.AR_ReconstructionLineEdit.hide()
            #deal with folder/file import
            self.AR_IsDicomFolderCheckBox.setChecked(False)
            self.AR_IsDicomFolderCheckBox.setEnabled(False)
        else:
            print("Error : [__UpdateModalityUI] Modality not recognized")

    def update_browseFile_UI(self, state):
        if state == 0: #unchecked
            self.AR_BrowsePushButton.setText("Browse File")
            self.AR_BrowseLineEdit.setText("")
        elif state == 2: #checked
            self.AR_BrowsePushButton.setText("Browse Folder")
            self.AR_BrowseLineEdit.setText("")
        else:
            print("Error : [__UpdateBrowseFileUI] State not recognized")

    def browse_for_file_to_add(self):
        modality = self.AR_ModalityComboBox.currentText()
        filters = {
            "(anat)": "Nifti files (*.nii *.nii.gz)",
            "photo (ieeg)": "Image files (*.png *.jpg *.tif)",
            "ieeg (ieeg)": "IEEG files (*.trc *.vhdr *.edf)"
        }

        if "(anat)" in modality and self.AR_IsDicomFolderCheckBox.isChecked(): # dicom folder
            folderPath = QFileDialog.getExistingDirectory(self, "Select a folder", self.__browse_folder_path_memory)
            if folderPath:
                self.__browse_folder_path_memory = folderPath
                self.AR_BrowseLineEdit.setText(folderPath)
        elif any(key in modality for key in filters): # nifti, photo, or ieeg file
            file_filter = next(filter for key, filter in filters.items() if key in modality)
            file_path = QFileDialog.getOpenFileName(self, "Select a file", self.__browse_folder_path_memory, filter=file_filter)
            if file_path[0]:
                self.__browse_folder_path_memory = os.path.dirname(file_path[0])
                self.AR_BrowseLineEdit.setText(file_path[0])
        else:
            QMessageBox.warning(self, "Modality not recognized", "Please select a modality first")

    def update_task_combobox_UI(self):
        if "Other" in self.AR_TaskComboBox.currentText():
            task_name = QInputDialog.getText(self, "Enter Task Name", "Enter a name for your task")[0]
            if task_name == "":
                QMessageBox.warning(self, "Dataset Name empty", "Please enter a valid name for your task")
                return
            else:
                self.AR_TaskComboBox.currentTextChanged.disconnect(self.update_task_combobox_UI)
                #Insert the new task in AR_TaskComboBox
                self.AR_TaskComboBox.insertItem(self.AR_TaskComboBox.count()-1, task_name)
                self.AR_TaskComboBox.setCurrentIndex(self.AR_TaskComboBox.count()-2)
                #Insert the new task in VE_TaskComboBox
                self.__ImportFileFileEditor.TaskComboBox.insertItem(self.__ImportFileFileEditor.TaskComboBox.count(), task_name)
                self.AR_TaskComboBox.currentTextChanged.connect(self.update_task_combobox_UI)

    def add_file_to_list(self):
        #Need to validate focus for ui elements in order to get all the values
        self.AR_TaskComboBox.clearFocus()
        self.AR_SessionComboBox.clearFocus()
        self.AR_ContrastAgentLineEdit.clearFocus()
        self.AR_AcquisitionLineEdit.clearFocus()
        self.AR_ReconstructionLineEdit.clearFocus()

        #Get file name
        file_path = self.AR_BrowseLineEdit.text()
        #Get only the filename
        file_name = os.path.basename(file_path)
        #Get the modality
        modality = self.AR_ModalityComboBox.currentText()
        #According to modality get the task and relevant elements from ui
        if "(anat)" in modality:
            task = ""
            session = self.AR_SessionComboBox.currentText()
            contrast_agent = self.AR_ContrastAgentLineEdit.text()
            acquisition = self.AR_AcquisitionLineEdit.text()
            reconstruction = self.AR_ReconstructionLineEdit.text()
        elif "ieeg (ieeg)" in modality:
            task = self.AR_TaskComboBox.currentText()
            session = self.AR_SessionComboBox.currentText()
            contrast_agent = ""
            acquisition = self.AR_AcquisitionLineEdit.text()
            reconstruction = ""
        elif "photo (ieeg)" in modality:
            task = ""
            session = self.AR_SessionComboBox.currentText()
            contrast_agent = ""
            acquisition = self.AR_AcquisitionLineEdit.text()
            reconstruction = ""
        else:
            print("Error : [__AddFileToList] Modality not recognized")

        subject = {
            "subject_id": self.AR_SubjectComboBox.currentText(),
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

        try:
            self.__ImportFileFileEditor.append_to_list(subject)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def start_file_import(self):
        # Check if a process is already running
        if hasattr(self, '__worker') and self.__worker.isRunning():
            print("[start_file_import] Import is already in progress")
            return

        # Get dataset path
        dataset_path =  self.fileTreeView.model().rootDirectory().path()

        # Create worker
        name = self.__ImportFileFileEditor._subject_data["subject_id"]
        files = self.__ImportFileFileEditor._subject_data["files"]
        self.__worker = ImportBidsFilesWorker(dataset_path, name, files)

        # Connect signals
        self.__worker.update_progressbar_signal.connect(self.progressBar.setValue)
        self.__worker.finished.connect(self.on_worker_finished)

        # Start the worker thread
        self.__worker.start()

    def start_subjects_import(self):
        # Check if a process is already running
        if hasattr(self, '__worker') and self.__worker.isRunning():
            print("[start_subjects_import] Import is already in progress")
            return

        # Get dataset path
        dataset_path =  self.fileTreeView.model().rootDirectory().path()

        # Create worker
        self.__worker = ImportBidsSubjectsWorker(dataset_path, self.__subject_data)

        # Connect signals
        self.__worker.update_progressbar_signal.connect(self.progressBar.setValue)
        self.__worker.finished.connect(self.on_worker_finished)

        # Start the worker thread
        self.__worker.start()

    def validate_bids_dataset(self):
        if not self.fileTreeView.model():
            QMessageBox.warning(self, "No Dataset found", "Please load a Dataset first")
            return

        dataset_path =  self.fileTreeView.model().rootDirectory().path()
        subject_name = "/" + self.AR_SubjectComboBox.currentText()
        print("Validating BIDS dataset at " + subject_name)

        # Validate BIDS dataset at /subject_name
        validator = BIDSValidator()

        #Get all files path of subject_name except files starting with . (hidden files)
        subject_path = dataset_path + subject_name
        subject_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(subject_path) for f in filenames if not f.startswith(".")]
        #strip dataset_path from the file path
        subject_files = [file.replace(dataset_path, "") for file in subject_files]

        res = True
        for file in subject_files:
            res = res and validator.is_bids(file)

        if res:
            QMessageBox.information(self, "Dataset compliant", self.AR_SubjectComboBox.currentText() + " is BIDS compliant")
        else:
            QMessageBox.warning(self, "Dataset not compliant", self.AR_SubjectComboBox.currentText() + " is not BIDS compliant")

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
        print("Cleaning up worker")
        self.__worker.deleteLater()  # Clean up the worker thread
