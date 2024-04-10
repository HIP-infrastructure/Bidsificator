from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QInputDialog, QTableWidgetItem, QMenu
from PyQt6.QtCore import QStandardPaths, Qt, QModelIndex
from PyQt6.QtGui import QFileSystemModel, QAction, QCursor

from core.BidsFolder import BidsFolder
from forms.MainWindow_ui import Ui_MainWindow
from workers.ImportBidsFilesWorker import ImportBidsFilesWorker

import os

class MainWindow(QMainWindow, Ui_MainWindow):
    __file_list = []
    __worker = None
    __selected_item = None

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.actionNew_Bids_Dataset.triggered.connect(self.__createDataset)
        self.actionOpen_Bids_Dataset.triggered.connect(self.__openDataset)

        # Connect UI
        #    First tab
        self.CreateSubjectPushButton.clicked.connect(self.__createSubject)
        self.tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.ShowSubjectListContextMenu)

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

    def __openDataset(self):
        folderPath = QFileDialog.getExistingDirectory(self, "Select a folder", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        if folderPath:
            self.__loadTreeViewUI(folderPath)
            self.__loadSubjectsInTableWidget()
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

    def __createDataset(self):        
        folderPath = QFileDialog.getExistingDirectory(self, "Select a folder to save the BIDS dataset", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        if folderPath:
            dataset_name = QInputDialog.getText(self, "Dataset Name", "Enter a name for the dataset")[0]
            if dataset_name == "":
                QMessageBox.warning(self, "Dataset Name empty", "Please enter a dataset name")
                return
        
            dataset_path = folderPath + os.sep + dataset_name

            participant_file_path = str(dataset_path) + os.sep +  "participants.tsv"
            dataset_description_file_path = str(dataset_path) + os.sep +  "dataset_description.json"

            bids_folder = BidsFolder(dataset_path)
            bids_folder.create_folders()
            bids_folder.generate_empty_dataset_description_file(dataset_name, dataset_description_file_path)
            bids_folder.generate_participants_tsv(participant_file_path)

            self.__loadTreeViewUI(dataset_path)
            self.__updateSubjectNamesDropDown()

    def __createSubject(self):
        subject_name = self.SubjectLineEdit.text()
        if subject_name == "":
            QMessageBox.warning(self, "Subject Name empty", "Please enter a subject name")
            return
    
        dataset_name = self.fileTreeView.model().rootDirectory().dirName()
        if dataset_name == "":
            QMessageBox.warning(self, "Dataset Name empty", "Please enter a dataset name")
            return
        
        dataset_path = self.fileTreeView.model().rootDirectory().path()

        participant_file_path = str(dataset_path) + "/participants.tsv"
        dataset_description_file_path = str(dataset_path) + "/dataset_description.json"

        bids_folder = BidsFolder(dataset_path)
        bids_folder.create_folders()
        bids_folder.generate_empty_dataset_description_file(dataset_name, dataset_description_file_path)

        subject_id = "sub-" + subject_name
        bids_subject = bids_folder.add_bids_subject(subject_id, subject_description={'age' : '123', 'sex' : 'M/F'})
        bids_folder.generate_participants_tsv(participant_file_path)

        self.__loadSubjectInTableWidget(bids_subject)
        self.__updateSubjectNamesDropDown()

    def ShowSubjectListContextMenu(self, event):
        index = self.tableWidget.indexAt(event)
        if not index.isValid():
            return
        self.__selected_item = self.tableWidget.indexAt(event)
        print(self.__selected_item.row())
        print(self.__selected_item.column())
        canAddKeyBefore = self.__selected_item.column() > 0

        self.customMenu = QMenu(self)
        addSubjectUnderAction = self.customMenu.addAction("Add Subject Under Selected")
        addSubjectAboveAction = self.customMenu.addAction("Add Subject Above Selected")
        deleteSelectedSubjectAction = self.customMenu.addAction("Remove Selected Subject")
        self.customMenu.addSeparator()
        addSelectedKeyAfterAction = self.customMenu.addAction("Add key after Selected")
        addSelectedKeyAfterAction.triggered.connect(self.addKeyAfterSelected)
        addKeyBeforeSelectedAction = self.customMenu.addAction("Add key before Selected")
        addKeyBeforeSelectedAction.setEnabled(canAddKeyBefore)
        addKeyBeforeSelectedAction.triggered.connect(self.addKeyBeforeSelected)
        removeSelectedKeyAction = self.customMenu.addAction("Remove Selected key")
        removeSelectedKeyAction.triggered.connect(self.removeSelectedKey)

        self.customMenu.popup(QCursor.pos())

    def addKeyBeforeSelected(self):        
        key, ok = QInputDialog.getText(self, "Add Key", "Enter a key")
        if ok and key:
            self.tableWidget.insertColumn(self.__selected_item.column())
            keyItem = QTableWidgetItem(key)
            keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tableWidget.setHorizontalHeaderItem(self.__selected_item.column(), keyItem)

            dataset_path = self.fileTreeView.model().rootDirectory().path()
            bids_folder = BidsFolder(dataset_path)
            subjects = bids_folder.get_bids_subects()
            for i, subject in enumerate(subjects):
                if key not in subject.get_optional_keys():
                    keyItem = QTableWidgetItem("n/a")
                    keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.tableWidget.setItem(i, self.__selected_item.column(), keyItem)    
                    #
                    subject.add_optional_key(key, keyItem.text())      

            participant_file_path = str(dataset_path) + "/participants.tsv"
            bids_folder.generate_participants_tsv(participant_file_path)

    def addKeyAfterSelected(self):        
        key, ok = QInputDialog.getText(self, "Add Key", "Enter a key")
        if ok and key:
            self.tableWidget.insertColumn(self.__selected_item.column() + 1)
            keyItem = QTableWidgetItem(key)
            keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tableWidget.setHorizontalHeaderItem(self.__selected_item.column() + 1, keyItem)

            dataset_path = self.fileTreeView.model().rootDirectory().path()
            bids_folder = BidsFolder(dataset_path)
            subjects = bids_folder.get_bids_subects()
            for i, subject in enumerate(subjects):
                if key not in subject.get_optional_keys():
                    keyItem = QTableWidgetItem("n/a")
                    keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.tableWidget.setItem(i, self.__selected_item.column() + 1, keyItem)    
                    #
                    subject.add_optional_key(key, keyItem.text())
            
            participant_file_path = str(dataset_path) + "/participants.tsv"
            bids_folder.generate_participants_tsv(participant_file_path)
    
    def removeSelectedKey(self):
        column_to_delete = self.__selected_item.column()

        #remove the key from the subject
        dataset_path = self.fileTreeView.model().rootDirectory().path()
        bids_folder = BidsFolder(dataset_path)
        subjects = bids_folder.get_bids_subects()
        for i, subject in enumerate(subjects):
            subject.remove_optional_key(self.tableWidget.horizontalHeaderItem(column_to_delete).text())

        #remove the column corresponding to the selected item
        self.tableWidget.removeColumn(column_to_delete)

        participant_file_path = str(dataset_path) + "/participants.tsv"
        bids_folder.generate_participants_tsv(participant_file_path)
    
    def __loadSubjectsInTableWidget(self):
        #cleanup
        self.tableWidget.setRowCount(0)

        dataset_path = self.fileTreeView.model().rootDirectory().path()
        bids_folder = BidsFolder(dataset_path)
        subjects = bids_folder.get_bids_subects()

        #We use a dict in order to keep the order of the elements + uniqueness
        all_optional_keys = {key: None for subject in subjects for key in subject.get_optional_keys().keys()}

        #Set horizontal header data
        all_optional_keys = list(all_optional_keys)
        self.tableWidget.setColumnCount(len(all_optional_keys) + 1)
        if all_optional_keys:
            self.tableWidget.setHorizontalHeaderLabels(["Subject ID"] + all_optional_keys)
        else:
            self.tableWidget.setHorizontalHeaderLabels(["Subject ID"])

        #Then fill the cells with participants data
        for subject in subjects:
            optional_keys = subject.get_optional_keys()
            rowPosition = self.tableWidget.rowCount()
            self.tableWidget.insertRow(rowPosition)
            subjectItem = QTableWidgetItem(subject.get_subject_id())
            subjectItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tableWidget.setItem(rowPosition, 0, subjectItem)
            for i, key in enumerate(all_optional_keys):
                keyItem = QTableWidgetItem(optional_keys.get(key, "n/a"))
                keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tableWidget.setItem(rowPosition, i + 1, keyItem)

    def __loadSubjectInTableWidget(self, bids_subject):
        rowPosition = self.tableWidget.rowCount()
        self.tableWidget.insertRow(rowPosition)

        # We use a dict in order to keep the order of the elements + uniqueness
        all_optional_keys = {self.tableWidget.horizontalHeaderItem(i).text(): None for i in range(1, self.tableWidget.columnCount())}
        if not all_optional_keys:
            all_optional_keys = {key: None for key in bids_subject.get_optional_keys()}

        #Set horizontal header data
        self.tableWidget.setColumnCount(len(all_optional_keys) + 1)
        self.tableWidget.setHorizontalHeaderLabels(["Subject ID"] + list(all_optional_keys))

        #Add subject id
        subjectItem = QTableWidgetItem(bids_subject.get_subject_id())
        subjectItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tableWidget.setItem(rowPosition, 0, subjectItem)
        #Add subject optional keys
        optional_keys = bids_subject.get_optional_keys()
        for i, key in enumerate(all_optional_keys):
            keyItem = QTableWidgetItem(optional_keys.get(key, "n/a"))
            keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tableWidget.setItem(rowPosition, i + 1, keyItem)

    def __updateSubjectNamesDropDown(self):
        dataset_path = self.fileTreeView.model().rootDirectory().path()
        subject_names = [f for f in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, f)) and not f.startswith(".") and f.startswith("sub-")]
        
        self.SubjectComboBox.clear()
        self.SubjectComboBox.addItems(subject_names)

    def __updateModalityUI(self):
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