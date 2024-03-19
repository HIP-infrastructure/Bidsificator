from PyQt6.QtWidgets import QMainWindow, QFileDialog
from PyQt6.QtCore import QDir, QObject, QStandardPaths, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFileSystemModel

from core.BidsFolder import BidsFolder
from forms.MainWindow_ui import Ui_MainWindow
from workers.ImportBidsFilesWorker import ImportBidsFilesWorker

import os

class MainWindow(QMainWindow, Ui_MainWindow):
    __file_list = []
    __isAlreadyRunning = False
    __thread = None
    __worker = None

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        # Connect UI
        self.BrowseDatasetPathPushButton.clicked.connect(self.__BrowseForFolder)
        self.CreateDatasetPushButton.clicked.connect(self.__CreateDataset)
        self.CreateSubjectPushButton.clicked.connect(self.__CreateSubject)
        self.ModlalityComboBox.currentIndexChanged.connect(self.__UpdateModalityUI)
        self.BrowsePushButton.clicked.connect(self.__BrowseForFileToAdd)
        self.IsDicomFolderCheckBox.stateChanged.connect(self.__UpdateBrowseFileUI)
        self.AddPushButton.clicked.connect(self.__AddFileToList)
        self.RemovePushButton.clicked.connect(self.__RemoveFileFromList)
        self.StartImportPushButton.clicked.connect(self.__StartFileImport)

        # Trigger UI for the first time
        self.progressBar.setValue(0)
        self.__UpdateModalityUI()

    def __BrowseForFolder(self):
        folderPath = QFileDialog.getExistingDirectory(self, "Select a folder", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        if folderPath:
            self.__LoadTreeViewUI(folderPath)
            self.DatasetPathLabel.setText(folderPath)
            self.__UpdateDatasetNamesDropDown()
            self.__UpdateSubjectNamesDropDown()

    def __LoadTreeViewUI(self, initial_folder):
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

    def __CreateDataset(self):
        dataset_name = self.DatasetLineEdit.text()
        dataset_path = self.DatasetPathLabel.text() + os.sep + dataset_name

        participant_file_path = str(dataset_path) + os.sep +  "participants.tsv"
        dataset_description_file_path = str(dataset_path) + os.sep +  "dataset_description.json"

        bids_folder = BidsFolder(dataset_path)
        bids_folder.create_folders()
        bids_folder.generate_empty_dataset_description_file(dataset_name, dataset_description_file_path)
        bids_folder.generate_participants_tsv(participant_file_path)

        self.__UpdateDatasetNamesDropDown()

    def __CreateSubject(self):
        subject_name = self.SubjectLineEdit.text()
        dataset_name = self.DatasetComboBox.currentText()
        dataset_path = self.DatasetPathLabel.text() + os.sep + dataset_name

        participant_file_path = str(dataset_path) + "/participants.tsv"
        dataset_description_file_path = str(dataset_path) + "/dataset_description.json"

        bids_folder = BidsFolder(dataset_path)
        bids_folder.create_folders()
        bids_folder.generate_empty_dataset_description_file("Dataset name", dataset_description_file_path)

        subject_id = "sub-" + subject_name
        bids_subject = bids_folder.add_bids_subject(subject_id)

        bids_folder.generate_participants_tsv(participant_file_path)

        self.__UpdateSubjectNamesDropDown()

    def __UpdateDatasetNamesDropDown(self):
        root_folder = self.DatasetPathLabel.text()
        # Get all the dir names from root_folder, remove those that starts with . or ..
        dataset_names = [f for f in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, f)) and not f.startswith(".")]

        # Add them to DatasetComboBox
        self.DatasetComboBox.clear()
        self.DatasetComboBox.addItems(dataset_names)
        self.DatasetComboBox.currentIndexChanged.connect(self.__UpdateSubjectNamesDropDown)

    def __UpdateSubjectNamesDropDown(self):
        dataset_name = self.DatasetComboBox.currentText()
        dataset_path = self.DatasetPathLabel.text() + os.sep + dataset_name
        subject_names = [f for f in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, f)) and not f.startswith(".") and f.startswith("sub-")]

        self.SubjectComboBox.clear()
        self.SubjectComboBox.addItems(subject_names)

    def __UpdateModalityUI(self):
        if "(anat)" in self.ModlalityComboBox.currentText():
            #session
            self.sessionLabel.show()
            self.sessionLineEdit.show()
            #task
            self.taskLabel.hide()
            self.taskLineEdit.hide()
            #contrast
            self.contrastAgentLabel.show()
            self.contrastAgentLineEdit.show()
            #acquisition
            self.acquisitionLabel.show()
            self.acquisitionLineEdit.show()
            #reconstruction
            self.reconstructionLabel.show()
            self.reconstructionLineEdit.show()
            #deal with folder/file import
            self.IsDicomFolderCheckBox.setEnabled(True)
        elif "(ieeg)" in self.ModlalityComboBox.currentText():
            #session
            self.sessionLabel.show()
            self.sessionLineEdit.show()
            #task
            self.taskLabel.show()
            self.taskLineEdit.show()
            #contrast
            self.contrastAgentLabel.hide()
            self.contrastAgentLineEdit.hide()
            #acquisition
            self.acquisitionLabel.show()
            self.acquisitionLineEdit.show()
            #reconstruction
            self.reconstructionLabel.hide()
            self.reconstructionLineEdit.hide()
            #deal with folder/file import
            self.IsDicomFolderCheckBox.setChecked(False)
            self.IsDicomFolderCheckBox.setEnabled(False)
        else:
            print("Error : [__UpdateModalityUI] Modality not recognized")

    def __UpdateBrowseFileUI(self, state):
        if state == 0: #unchecked
            self.BrowsePushButton.setText("Browse File")
        elif state == 2: #checked
            self.BrowsePushButton.setText("Browse Folder")
        else:
            print("Error : [__UpdateBrowseFileUI] State not recognized")

    def __BrowseForFileToAdd(self):
        if "(anat)" in self.ModlalityComboBox.currentText() and self.IsDicomFolderCheckBox.isChecked():
            folderPath = QFileDialog.getExistingDirectory(self, "Select a folder", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
            if folderPath:
                self.BrowseLineEdit.setText(folderPath)
        else:
            file_path = QFileDialog.getOpenFileName(self, "Select a file", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
            if file_path:
                self.BrowseLineEdit.setText(file_path[0])
    
    def __AddFileToList(self):
        #Get file name
        file_path = self.BrowseLineEdit.text()
        #Get only the filename
        file_name = os.path.basename(file_path)
        #Get the modality
        modality = self.ModlalityComboBox.currentText()
        #According to modality get the task and relevant elements from ui 
        if "(anat)" in modality:
            task = None
            session = self.sessionLineEdit.text()
            contrast_agent = self.contrastAgentLineEdit.text()
            acquisition = self.acquisitionLineEdit.text()
            reconstruction = self.reconstructionLineEdit.text()
        elif "(ieeg)" in modality:
            task = self.taskLineEdit.text()
            session = self.sessionLineEdit.text()
            contrast_agent = None
            acquisition = self.acquisitionLineEdit.text()
            reconstruction = None
        else:
            print("Error : [__AddFileToList] Modality not recognized")

        file = {
            "file_name": file_name,
            "file_path": file_path,
            "modality": modality,
            "task": task,
            "session": session,
            "contrast_agent": contrast_agent,
            "acquisition": acquisition,
            "reconstruction": reconstruction
        }
        self.__file_list.append(file)
        self.fileListWidget.addItem(file["file_name"])

        #When click on element in fileListWidget , print the relevant elements in the ui
        self.fileListWidget.itemClicked.connect(self.__ShowUiElementDetails)

    def __ShowUiElementDetails(self):
        item = self.fileListWidget.currentItem()
        #Check if item is not None and is in __file_list with key file_name
        if item and item.text() in [file["file_name"] for file in self.__file_list]:
            #Get the file from __file_list and check if element is found
            file = [file for file in self.__file_list if file["file_name"] == item.text()][0]

            if "(anat)" in file["modality"]:
                self.SessionLabel.setText("Session : " + file["session"])
                self.TaskLabel.setText("Task :")
                self.ContrastAgentLabel.setText("Contrast Agent : " + file["contrast_agent"])
                self.AcquisitionLabel.setText("Acquisition : " + file["acquisition"])
                self.ReconstructionLabel.setText("Reconstruction : " + file["reconstruction"])
                self.FilePathLabel.setText("Path : " + file["file_path"])
            elif "(ieeg)" in file["modality"]:
                self.SessionLabel.setText("Session : " + file["session"])
                self.TaskLabel.setText("Task : " + file["task"])
                self.ContrastAgentLabel.setText("Contrast Agent :")
                self.AcquisitionLabel.setText("Acquisition : " + file["acquisition"])
                self.ReconstructionLabel.setText("Reconstruction :")
                self.FilePathLabel.setText("Path : " + file["file_path"])
        else:
            self.SessionLabel.setText("Session :")
            self.TaskLabel.setText("Task :")
            self.ContrastAgentLabel.setText("Contrast Agent :")
            self.AcquisitionLabel.setText("Acquisition :")
            self.ReconstructionLabel.setText("Reconstruction :")
            self.FilePathLabel.setText("Path :")

    def __RemoveFileFromList(self):
        #Get clicked item
        item = self.fileListWidget.currentItem()
        #Check if item is not None and is in __file_list with key file_name
        if item and item.text() in [file["file_name"] for file in self.__file_list]:
            #Get the file from __file_list and check if element is found
            file = [file for file in self.__file_list if file["file_name"] == item.text()][0]
            #Remove the file from __file_list
            self.__file_list.remove(file)
            #Remove the item from fileListWidget
            self.fileListWidget.takeItem(self.fileListWidget.currentRow())
            #Update UI 
            self.__ShowUiElementDetails()
        else:
            print("Error : [__RemoveFileFromList] Item not found in __file_list")

    def __StartFileImport(self):
        #Get root folder
        root_folder = self.DatasetPathLabel.text()
        #Get dataset name
        dataset_name = self.DatasetComboBox.currentText()
        #Get dataset path
        dataset_path = root_folder + os.sep + dataset_name
        #Get subject name
        subject_name = self.SubjectComboBox.currentText()

        #Create worker and thread
        self.__worker = ImportBidsFilesWorker(dataset_path, subject_name, self.__file_list)
        self.__thread = QThread()

        # Event From worker and thread
        self.__worker.update_progressbar_signal.connect(self.progressBar.setValue)
        self.__worker.finished.connect(self.__thread.quit)
        self.__worker.finished.connect(self.__worker.deleteLater)
        self.__thread.finished.connect(self.__thread.deleteLater)
        self.__thread.started.connect(self.__worker.Process)
        self.__worker.finished.connect(lambda: setattr(self, '__isAlreadyRunning', False))

        # Launch Thread and lock possible second launch
        self.__worker.moveToThread(self.__thread)
        self.__thread.start()
        self.__isAlreadyRunning = True