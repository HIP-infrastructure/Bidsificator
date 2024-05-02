from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QInputDialog, QTableWidgetItem, QMenu, QTreeView
from PyQt6.QtCore import QStandardPaths, Qt, QModelIndex, QAbstractItemModel
from PyQt6.QtGui import QFileSystemModel, QAction, QCursor

from core.BidsFolder import BidsFolder
from forms.MainWindow_ui import Ui_MainWindow
from workers.ImportBidsFilesWorker import ImportBidsFilesWorker

import os

class MainWindow(QMainWindow, Ui_MainWindow):
    __file_list = []
    __worker = None

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.actionNew_Bids_Dataset.triggered.connect(self.__createDataset)
        self.actionOpen_Bids_Dataset.triggered.connect(self.__openDataset)

        # Connect UI
        #    First tab
        self.CreateSubjectPushButton.clicked.connect(self.__createSubject)
        self.SubjectLineEdit.setCursorPosition(len(self.SubjectLineEdit.text()))
        #    Second tab
        self.ModlalityComboBox.currentIndexChanged.connect(self.__updateModalityUI)
        self.BrowsePushButton.clicked.connect(self.__browseForFileToAdd)
        self.IsDicomFolderCheckBox.stateChanged.connect(self.__updateBrowseFileUI)
        self.AddPushButton.clicked.connect(self.__addFileToList)
        self.RemovePushButton.clicked.connect(self.__removeFileFromList)
        self.StartImportPushButton.clicked.connect(self.__startFileImport)

        # Trigger UI for the first time
        self.progressBar.setValue(0)
        self.__updateModalityUI()

    def debug(self, oldPos, newPos):
        print("Old position : " + str(oldPos))
        print("New position : " + str(newPos))

    def __createDataset(self):        
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

            self.__loadTreeViewUI(dataset_path)
            self.tableWidget.LoadSubjectsInTableWidget(dataset_path)
            self.__updateSubjectNamesDropDown()

    def __openDataset(self):
        folderPath = QFileDialog.getExistingDirectory(self, "Select a folder", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        if folderPath:
            self.__loadTreeViewUI(folderPath)
            self.tableWidget.LoadSubjectsInTableWidget(folderPath)
            self.__updateSubjectNamesDropDown()

    def __loadTreeViewUI(self, initial_folder):
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

    def __createSubject(self):
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
        self.__updateSubjectNamesDropDown()
    
    def __updateSubjectNamesDropDown(self):
        dataset_path = self.fileTreeView.model().rootDirectory().path()
        subject_names = [f for f in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, f)) and not f.startswith(".") and f.startswith("sub-")]
        
        self.SubjectComboBox.currentTextChanged.connect(self.__updateSubjectDetails)
        self.SubjectComboBox.clear()
        self.SubjectComboBox.addItems(subject_names)

    def __updateSubjectDetails(self):
        dataset_path = self.fileTreeView.model().rootDirectory().path()
        subject_name = self.SubjectComboBox.currentText()
        subject_path = os.path.join(dataset_path, subject_name)

        session_names = [f for f in os.listdir(subject_path) if os.path.isdir(os.path.join(subject_path, f)) and not f.startswith(".") and f.startswith("ses-")]
        self.sessionComboBox.clear()
        self.sessionComboBox.addItems(session_names)

    def __updateModalityUI(self):
        if "(anat)" in self.ModlalityComboBox.currentText():
            #session
            self.sessionLabel.show()
            self.sessionComboBox.show()
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
            self.sessionComboBox.show()
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

    def __updateBrowseFileUI(self, state):
        if state == 0: #unchecked
            self.BrowsePushButton.setText("Browse File")
            self.BrowseLineEdit.setText("")
        elif state == 2: #checked
            self.BrowsePushButton.setText("Browse Folder")
            self.BrowseLineEdit.setText("")
        else:
            print("Error : [__UpdateBrowseFileUI] State not recognized")

    def __browseForFileToAdd(self):
        if "(anat)" in self.ModlalityComboBox.currentText() and self.IsDicomFolderCheckBox.isChecked():
            folderPath = QFileDialog.getExistingDirectory(self, "Select a folder", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
            if folderPath:
                self.BrowseLineEdit.setText(folderPath)
        else:
            file_path = QFileDialog.getOpenFileName(self, "Select a file", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
            if file_path:
                self.BrowseLineEdit.setText(file_path[0])
    
    def __addFileToList(self):
        #Get file name
        file_path = self.BrowseLineEdit.text()
        #Get only the filename
        file_name = os.path.basename(file_path)
        #Get the modality
        modality = self.ModlalityComboBox.currentText()
        #According to modality get the task and relevant elements from ui 
        if "(anat)" in modality:
            task = None
            session = self.sessionComboBox.text()
            contrast_agent = self.contrastAgentLineEdit.text()
            acquisition = self.acquisitionLineEdit.text()
            reconstruction = self.reconstructionLineEdit.text()
        elif "(ieeg)" in modality:
            task = self.taskLineEdit.text()
            session = self.sessionComboBox.text()
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

        # file = {
        #     "file_name": 'LYONNEURO_2019_LUIv_LEC1.TRC',
        #     "file_path": '/Users/florian/Documents/Arbeit/CRNL/Data/Database/LOCA_DB/2019/LYONNEURO_2019_LUIv/LYONNEURO_2019_LUIv_LEC1/LYONNEURO_2019_LUIv_LEC1.TRC',
        #     "modality": 'ieeg (ieeg)',
        #     "task": 'LEC1',
        #     "session": 'post',
        #     "contrast_agent": '',
        #     "acquisition": '01',
        #     "reconstruction": ''
        # }
        # self.__file_list.append(file)
        # self.fileListWidget.addItem(file["file_name"])

        # file = {
        #     "file_name": 'LYONNEURO_2019_LUIv_LEC2.TRC',
        #     "file_path": '/Users/florian/Documents/Arbeit/CRNL/Data/Database/LOCA_DB/2019/LYONNEURO_2019_LUIv/LYONNEURO_2019_LUIv_LEC2/LYONNEURO_2019_LUIv_LEC2.TRC',
        #     "modality": 'ieeg (ieeg)',
        #     "task": 'LEC2',
        #     "session": 'post',
        #     "contrast_agent": '',
        #     "acquisition": '01',
        #     "reconstruction": ''
        # }
        # self.__file_list.append(file)
        # self.fileListWidget.addItem(file["file_name"])

        #When click on element in fileListWidget , print the relevant elements in the ui
        self.fileListWidget.itemClicked.connect(self.__showUiElementDetails)

    def __showUiElementDetails(self):
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

    def __removeFileFromList(self):
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
            self.__showUiElementDetails()
        else:
            print("Error : [__RemoveFileFromList] Item not found in __file_list")

    def __startFileImport(self):
        # Get dataset path
        dataset_path =  self.fileTreeView.model().rootDirectory().path()
        # Get subject name
        subject_name = self.SubjectComboBox.currentText()

        # Check if a process is already running
        if hasattr(self, '__worker') and self.__worker.isRunning():
            print("Import is already in progress")
            return

        # Create worker
        self.__worker = ImportBidsFilesWorker(dataset_path, subject_name, self.__file_list)

        # Connect signals
        self.__worker.update_progressbar_signal.connect(self.progressBar.setValue)
        self.__worker.finished.connect(self.__onWorkerFinished)

        # Start the worker thread
        self.__worker.start()

    def __onWorkerFinished(self):
        """Display a completion message and handle cleanup after the worker thread finishess"""

        print("File import finished")
        self.__worker.deleteLater()  # Clean up the worker thread