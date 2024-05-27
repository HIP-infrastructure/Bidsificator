from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QInputDialog, QTableWidgetItem, QMenu, QTreeView
from PyQt6.QtCore import QStandardPaths, Qt, QModelIndex, QAbstractItemModel
from PyQt6.QtGui import QFileSystemModel, QAction, QCursor

from core.BidsFolder import BidsFolder
from forms.MainWindow_ui import Ui_MainWindow
from workers.ImportBidsFilesWorker import ImportBidsFilesWorker
from bids_validator import BIDSValidator

import os

class MainWindow(QMainWindow, Ui_MainWindow):
    __file_list = []
    __worker = None
    __item_memory = None
    __lock_for_update = False
    __browse_folder_path_memory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.actionNew_Bids_Dataset.triggered.connect(self.create_dataset)
        self.actionOpen_Bids_Dataset.triggered.connect(self.open_dataset)

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
        self.AR_AddPushButton.clicked.connect(self.add_file_to_list)
        self.AR_RemovePushButton.clicked.connect(self.remove_file_from_list)
        #       View/Edit file
        self.VE_FileListWidget.itemClicked.connect(self.show_element_details_UI)
        self.VE_FileListWidget.itemSelectionChanged.connect(self.show_element_details_UI)
        
        self.VE_ModalityComboBox.currentTextChanged.connect(self.textEdited)
        self.VE_SessionComboBox.currentTextChanged.connect(self.textEdited)
        self.VE_TaskLineEdit.textEdited.connect(self.textEdited)
        self.VE_TaskLineEdit.editingFinished.connect(self.editingFinished)
        self.VE_ContrastAgentLineEdit.textEdited.connect(self.textEdited)
        self.VE_ContrastAgentLineEdit.editingFinished.connect(self.editingFinished)
        self.VE_AcquisitionLineEdit.textEdited.connect(self.textEdited)
        self.VE_AcquisitionLineEdit.editingFinished.connect(self.editingFinished)
        self.VE_ReconstructionLineEdit.textEdited.connect(self.textEdited)
        self.VE_ReconstructionLineEdit.editingFinished.connect(self.editingFinished)
        self.VE_PathLineEdit.textEdited.connect(self.textEdited)
        self.VE_PathLineEdit.editingFinished.connect(self.editingFinished)

        self.VE_EditPushButton.clicked.connect(self.toggle_edit_fields)
        self.VE_CancelPushButton.clicked.connect(self.reset_edit_fields_from_memory)
        #       Buttons           
        self.StartImportPushButton.clicked.connect(self.start_file_import)
        self.BidsValidatorPushButton.clicked.connect(self.validate_bids_dataset)

        # Trigger UI for the first time
        self.progressBar.setValue(0)
        self.update_modality_UI()

    def create_dataset(self):        
        folderPath = QFileDialog.getExistingDirectory(self, "Select a folder to save the BIDS dataset", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        if folderPath:
            dataset_name = QInputDialog.getText(self, "Dataset Name", "Enter a name for the dataset")[0]
            if dataset_name == "":
                QMessageBox.warning(self, "Dataset Name empty", "Please enter a dataset name")
                return
        
            dataset_path = folderPath + os.sep + dataset_name

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
        self.VE_SessionComboBox.clear()
        self.VE_SessionComboBox.addItems(session_names)

    def update_modality_UI(self):
        if "(anat)" in self.AR_ModalityComboBox.currentText():
            #session
            self.AR_SessionLabel.show()
            self.AR_SessionComboBox.show()
            #task
            self.AR_TaskLabel.hide()
            self.AR_TaskLineEdit.hide()
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
            self.AR_TaskLineEdit.show()
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
            self.AR_TaskLineEdit.hide()
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
    
    def add_file_to_list(self):
        #Need to validate focus for ui elements in order to get all the values
        self.AR_TaskLineEdit.clearFocus()
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
            task = self.AR_TaskLineEdit.text()
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
            
        file = {
            "file_name": file_name,
            "file_path": file_path,
            "modality": modality,
            "task": task,
            "session": session.removeprefix("ses-"),
            "contrast_agent": contrast_agent,
            "acquisition": acquisition,
            "reconstruction": reconstruction
        }

        if file not in self.__file_list:
            self.__file_list.append(file)
            self.VE_FileListWidget.addItem(file["file_name"])
        else:
            QMessageBox.warning(self, "File already added", "This file has already been added to the list")

    def show_element_details_UI(self):
        self.__lock_for_update = True
        selectedIndexes = self.VE_FileListWidget.selectedIndexes() 
        if len(selectedIndexes) > 0:
            file = self.__file_list[selectedIndexes[0].row()]
            self.__item_memory = file
            if "(anat)" in file["modality"]:
                self.set_comboBox_text(self.VE_ModalityComboBox, file["modality"])
                self.set_comboBox_text(self.VE_SessionComboBox, str("ses-" + file["session"]))
                self.VE_TaskLineEdit.setText("")
                self.VE_ContrastAgentLineEdit.setText(file["contrast_agent"])
                self.VE_AcquisitionLineEdit.setText(file["acquisition"])
                self.VE_ReconstructionLineEdit.setText(file["reconstruction"])
                self.VE_PathLineEdit.setText(file["file_path"])
            elif "(ieeg)" in file["modality"]:
                self.set_comboBox_text(self.VE_ModalityComboBox, file["modality"])
                self.set_comboBox_text(self.VE_SessionComboBox, str("ses-" + file["session"]))
                self.VE_TaskLineEdit.setText(file["task"])
                self.VE_ContrastAgentLineEdit.setText("")
                self.VE_AcquisitionLineEdit.setText(file["acquisition"])
                self.VE_ReconstructionLineEdit.setText("")
                self.VE_PathLineEdit.setText(file["file_path"])
        else:
            self.set_comboBox_text(self.VE_ModalityComboBox, "")
            self.set_comboBox_text(self.VE_SessionComboBox, "")
            self.VE_TaskLineEdit.setText("")
            self.VE_ContrastAgentLineEdit.setText("")
            self.VE_AcquisitionLineEdit.setText("")
            self.VE_ReconstructionLineEdit.setText("")
            self.VE_PathLineEdit.setText("")            
        self.__lock_for_update = False

    def remove_file_from_list(self):
        selectedIndexes = self.VE_FileListWidget.selectedIndexes() 
        if len(selectedIndexes) > 0:
            file = self.__file_list[selectedIndexes[0].row()]
            #Remove the file from __file_list
            self.__file_list.remove(file)
            #Remove the item from fileListWidget
            self.VE_FileListWidget.takeItem(self.VE_FileListWidget.currentRow())
            #Update UI 
            self.show_element_details_UI()
        else:
            print("Error : [__RemoveFileFromList] Item not found in __file_list")

    def toggle_edit_fields(self):
        newStatus = not self.VE_TaskLineEdit.isEnabled()
        if not newStatus and self.was_element_modified_UI():
            index = self.__file_list.index(self.__item_memory)
            file = {
                "file_name": self.VE_FileListWidget.currentItem().text(),
                "file_path": self.VE_PathLineEdit.text(),
                "modality": self.VE_ModalityComboBox.currentText(),
                "task": self.VE_TaskLineEdit.text(),
                "session": self.VE_SessionComboBox.currentText(),
                "contrast_agent": self.VE_ContrastAgentLineEdit.text(),
                "acquisition": self.VE_AcquisitionLineEdit.text(),
                "reconstruction": self.VE_ReconstructionLineEdit.text()
            }
            self.__file_list[index] = file
            self.__item_memory = file                

        newStatusLabel = "Editing" if newStatus else "Edit"
        self.VE_EditPushButton.setText(newStatusLabel)
        self.VE_FileListWidget.setEnabled(not newStatus)

        self.VE_ModalityComboBox.setEnabled(newStatus)
        self.VE_SessionComboBox.setEnabled(newStatus)
        self.VE_TaskLineEdit.setEnabled(newStatus)
        self.VE_ContrastAgentLineEdit.setEnabled(newStatus)
        self.VE_AcquisitionLineEdit.setEnabled(newStatus)
        self.VE_ReconstructionLineEdit.setEnabled(newStatus)
        self.VE_PathLineEdit.setEnabled(newStatus)

    def reset_edit_fields_from_memory(self):
        self.set_comboBox_text(self.VE_ModalityComboBox, self.__item_memory["modality"])
        self.set_comboBox_text(self.VE_SessionComboBox, str("ses-" + self.__item_memory["session"]))
        self.VE_TaskLineEdit.setText(self.__item_memory['task'])
        self.VE_ContrastAgentLineEdit.setText(self.__item_memory['contrast_agent'])
        self.VE_AcquisitionLineEdit.setText(self.__item_memory['acquisition'])
        self.VE_ReconstructionLineEdit.setText(self.__item_memory['reconstruction'])
        self.VE_PathLineEdit.setText(self.__item_memory['file_path'])
        #Clear focus to trigger editingFinished
        self.VE_ModalityComboBox.clearFocus()
        self.VE_SessionComboBox.clearFocus()
        self.VE_TaskLineEdit.clearFocus()
        self.VE_ContrastAgentLineEdit.clearFocus()
        self.VE_AcquisitionLineEdit.clearFocus()
        self.VE_ReconstructionLineEdit.clearFocus()
        self.VE_PathLineEdit.clearFocus()

    def was_element_modified_UI(self):
        if not self.__item_memory:
            return False
        
        file = {
            "file_name": self.VE_FileListWidget.currentItem().text(),
            "file_path": self.VE_PathLineEdit.text(),
            "modality": self.VE_ModalityComboBox.currentText(),
            "task": self.VE_TaskLineEdit.text(),
            "session": self.VE_SessionComboBox.currentText().removeprefix("ses-"),
            "contrast_agent": self.VE_ContrastAgentLineEdit.text(),
            "acquisition": self.VE_AcquisitionLineEdit.text(),
            "reconstruction": self.VE_ReconstructionLineEdit.text()
        }
        print("tutu")
        same_file_name = self.__item_memory['file_name'] == file['file_name']
        same_file_path = self.__item_memory['file_path'] == file['file_path']
        same_modality = self.__item_memory['modality'] == file['modality']
        same_task = self.__item_memory['task'] == file['task']
        same_session = self.__item_memory['session'] == file['session']
        same_contrast_agent = self.__item_memory['contrast_agent'] == file['contrast_agent']
        same_acquisition = self.__item_memory['acquisition'] == file['acquisition']
        same_reconstruction = self.__item_memory['reconstruction'] == file['reconstruction']

        print(self.__item_memory['file_name'] + " == " + file['file_name'])
        print("Same file name :" + str(same_file_name))
        print(self.__item_memory['file_path'] + " == " + file['file_path'])
        print("Same file path :" + str(same_file_path))
        print(self.__item_memory['modality'] + " == " + file['modality'])
        print("Same modality :" + str(same_modality))
        print(self.__item_memory['task'] + " == " + file['task'])
        print("Same task :" + str(same_task))
        print(self.__item_memory['session'] + " == " + file['session'])
        print("Same session :" + str(same_session))
        print(self.__item_memory['contrast_agent'] + " == " + file['contrast_agent'])
        print("Same contrast agent :" + str(same_contrast_agent))
        print(self.__item_memory['acquisition'] + " == " + file['acquisition'])
        print("Same acquisition :" + str(same_acquisition))
        print(self.__item_memory['reconstruction'] + " == " + file['reconstruction'])
        print("Same reconstruction :" + str(same_reconstruction))
        print("--------")

        return not(same_file_name and same_file_path and same_modality and same_task and same_session and same_contrast_agent and same_acquisition and same_reconstruction)

    def start_file_import(self):
        # Get dataset path
        dataset_path =  self.fileTreeView.model().rootDirectory().path()
        # Get subject name
        subject_name = self.AR_SubjectComboBox.currentText()

        # Check if a process is already running
        if hasattr(self, '__worker') and self.__worker.isRunning():
            print("Import is already in progress")
            return

        # Create worker
        self.__worker = ImportBidsFilesWorker(dataset_path, subject_name, self.__file_list)

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
        self.__worker.deleteLater()  # Clean up the worker thread

    def textEdited(self, text):
        #print("Text edited : " + text)
        if not self.__lock_for_update:
            self.VE_CancelPushButton.setEnabled(self.was_element_modified_UI())

    def editingFinished(self):
        #print("Editing finished")
        if not self.__lock_for_update:
            self.VE_CancelPushButton.setEnabled(self.was_element_modified_UI())
