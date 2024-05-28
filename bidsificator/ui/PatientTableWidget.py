from PyQt6.QtWidgets import QHeaderView, QMenu, QTableWidget, QTableWidgetItem, QMenu, QInputDialog, QTableWidgetItem, QMenu, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor

from core.BidsFolder import BidsFolder

class PatientTableWidget(QTableWidget):
    __selected_item = None
    __bids_folder = None
    __previous_cell_text = None
    subject_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.ShowHorizontalContextMenu)
        self.verticalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.verticalHeader().customContextMenuRequested.connect(self.ShowVerticalContextMenu)

    def __connectTableWidget(self):
        self.itemClicked.connect(self.ItemClicked)
        self.itemChanged.connect(self.ItemChanged)

    def __disconnectTableWidget(self):
        """
        Disconnects the `itemClicked` and `itemChanged` signals from their respective slots.
        This method attempts to disconnect the `itemClicked` signal from the `ItemClicked` slot and the `itemChanged` signal from the `ItemChanged` slot. 
        If a signal is not connected to its slot, a `TypeError` is raised and caught, allowing the method to continue.
        
        Raises:
            TypeError: If a signal is not connected to its slot. This exception is caught and does not interrupt the method.
        """
        try:
            self.itemClicked.disconnect(self.ItemClicked)
        except TypeError:
            pass   
        try:
            self.itemChanged.disconnect(self.ItemChanged)
        except TypeError:
            pass

    def ShowHorizontalContextMenu(self, event):
        index = self.indexAt(event)
        if not index.isValid():
            return
        self.__selected_item = self.indexAt(event)
        print("Horizontal Context Menu")
        print(str(self.__selected_item.row()) + " " + str(self.__selected_item.column()))
        canAddKeyBefore = self.__selected_item.column() > 0

        self.customMenu = QMenu(self)
        addSelectedKeyAfterAction = self.customMenu.addAction("Add key after Selected")
        addSelectedKeyAfterAction.triggered.connect(self.AddKeyAfterSelected)
        addKeyBeforeSelectedAction = self.customMenu.addAction("Add key before Selected")
        addKeyBeforeSelectedAction.setEnabled(canAddKeyBefore)
        addKeyBeforeSelectedAction.triggered.connect(self.AddKeyBeforeSelected)
        removeSelectedKeyAction = self.customMenu.addAction("Remove Selected key")
        removeSelectedKeyAction.triggered.connect(self.RemoveSelectedKey)

        self.customMenu.popup(QCursor.pos())

    def ShowVerticalContextMenu(self, event):
        index = self.indexAt(event)
        if not index.isValid():
            return
        self.__selected_item = self.indexAt(event)
        print("Vertical Context Menu")
        print(str(self.__selected_item.row()) + " " + str(self.__selected_item.column()))

        self.customMenu = QMenu(self)
        deleteSelectedSubjectAction = self.customMenu.addAction("Remove Selected Subject")
        deleteSelectedSubjectAction.triggered.connect(self.DeleteSelectedSubject)
        
        self.customMenu.popup(QCursor.pos())

    def GetSubjectsKeysFromTable(self):
        default_values = {'age' : '123', 'sex' : 'M/F'}
        subjects_keys = {self.horizontalHeaderItem(i).text(): default_values.get(self.horizontalHeaderItem(i).text().lower(), "n/a") for i in range(1, self.columnCount())}
        if "Subject ID" in subjects_keys:
            del subjects_keys["Subject ID"]
        return subjects_keys
    
    def LoadSubjectsInTableWidget(self, dataset_path: str):
        #cleanup
        self.setRowCount(0)

        #dataset_path = self.fileTreeView.model().rootDirectory().path()
        self.__bids_folder = BidsFolder(dataset_path)
        subjects = self.__bids_folder.get_bids_subjects()

        #We use a dict in order to keep the order of the elements + uniqueness
        all_optional_keys = {key: None for subject in subjects for key in subject.get_optional_keys().keys()}

        #Set horizontal header data
        all_optional_keys = list(all_optional_keys)
        self.setColumnCount(len(all_optional_keys) + 1)
        if all_optional_keys:
            self.setHorizontalHeaderLabels(["Subject ID"] + all_optional_keys)
        else:
            self.setHorizontalHeaderLabels(["Subject ID"])

        self.__disconnectTableWidget()
        #Then fill the cells with participants data
        for subject in subjects:
            optional_keys = subject.get_optional_keys()
            rowPosition = self.rowCount()
            self.insertRow(rowPosition)
            subjectItem = QTableWidgetItem(subject.get_subject_id())
            subjectItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(rowPosition, 0, subjectItem)
            for i, key in enumerate(all_optional_keys):
                keyItem = QTableWidgetItem(optional_keys.get(key, "n/a"))
                keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(rowPosition, i + 1, keyItem)
        self.__connectTableWidget()

    def CreateSubjectInTableWidget(self,subject_name: str):
        subject_description = self.GetSubjectsKeysFromTable()
        print("subject_description: " + str(subject_description))
        if not subject_description:
            subject_description = {'age' : '123', 'sex' : 'M/F'}
        print("subject_description after check not: " + str(subject_description))

        bids_subject = self.__bids_folder.add_bids_subject(subject_name, subject_description)
        self.__bids_folder.generate_participants_tsv()

        #insert a new row
        rowPosition = self.rowCount()
        self.insertRow(rowPosition)

        #Set horizontal header data
        subject_description_list = list(subject_description)
        self.setColumnCount(len(subject_description_list) + 1)
        if subject_description_list:
            self.setHorizontalHeaderLabels(["Subject ID"] + subject_description_list)
        else:
            self.setHorizontalHeaderLabels(["Subject ID"])

        self.__disconnectTableWidget()
        #Add subject id
        subjectItem = QTableWidgetItem(bids_subject.get_subject_id())
        subjectItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(rowPosition, 0, subjectItem)
        #Add subject optional keys
        for i, key in enumerate(subject_description):
            keyItem = QTableWidgetItem(subject_description.get(key, "n/a"))
            keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(rowPosition, i + 1, keyItem)
        self.__connectTableWidget()

    def AddKeyBeforeSelected(self):        
        key, ok = QInputDialog.getText(self, "Add Key", "Enter a key")
        if ok and key:
            currentIndex = self.__selected_item.column()
            self.insertColumn(currentIndex)
            keyItem = QTableWidgetItem(key)
            keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setHorizontalHeaderItem(currentIndex, keyItem)

            subjects = self.__bids_folder.get_bids_subjects()
            for i, subject in enumerate(subjects):
                if key not in subject.get_optional_keys():
                    keyItem = QTableWidgetItem("n/a")
                    keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.setItem(i, currentIndex, keyItem)    
                    #
                    subject.add_optional_key_at(currentIndex - 1, key, keyItem.text())      

            self.__bids_folder.generate_participants_tsv()

    def AddKeyAfterSelected(self):        
        key, ok = QInputDialog.getText(self, "Add Key", "Enter a key")
        if ok and key:
            currentIndex = self.__selected_item.column() + 1
            self.insertColumn(currentIndex)
            keyItem = QTableWidgetItem(key)
            keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setHorizontalHeaderItem(currentIndex, keyItem)

            subjects = self.__bids_folder.get_bids_subjects()
            for i, subject in enumerate(subjects):
                if key not in subject.get_optional_keys():
                    keyItem = QTableWidgetItem("n/a")
                    keyItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.setItem(i, currentIndex, keyItem)    
                    #
                    subject.add_optional_key_at(currentIndex - 1, key, keyItem.text())
            
            self.__bids_folder.generate_participants_tsv()
    
    def RemoveSelectedKey(self):
        column_to_delete = self.__selected_item.column()
        key_to_delete = self.horizontalHeaderItem(column_to_delete).text()
        
        return_value = QMessageBox.warning(self, "Delete Key", "Are you sure you want to delete the key " + key_to_delete + "?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if return_value == QMessageBox.StandardButton.Yes:
            #Remove for each subject in the data structures
            subjects = self.__bids_folder.get_bids_subjects()
            for subject in subjects:
                subject.remove_optional_key(key_to_delete)

            #remove the column corresponding to the selected item
            self.removeColumn(column_to_delete)

            #update the participants.tsv file
            self.__bids_folder.generate_participants_tsv()

    def DeleteSelectedSubject(self):
        row_to_delete = self.__selected_item.row()
        subject_id = self.item(row_to_delete, 0).text()

        return_value = QMessageBox.warning(self, "Delete Subject", "Are you sure you want to delete the subject " + subject_id + "?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if return_value == QMessageBox.StandardButton.Yes:
            #remove from the data structure
            self.__bids_folder.delete_bids_subject(subject_id)
            #remove the rown corresponding to the selected subject
            self.removeRow(row_to_delete)
            #update the participants.tsv file
            self.__bids_folder.generate_participants_tsv()

    def ItemChanged(self, item):
        print("Item changed")
        print("row: " + str(item.row()) + " column: " + str(item.column()))
        print("text: " + item.text())
        if item.column() == 0:
            subject_id = self.__previous_cell_text
            subject = self.__bids_folder.get_bids_subject(subject_id)
            subject.set_subject_id(item.text())
            self.__bids_folder.generate_participants_tsv()
            self.subject_updated.emit()
        else:
            subject_id = self.item(item.row(), 0).text()
            key = self.horizontalHeaderItem(item.column()).text()
            self.__bids_folder.get_bids_subject(subject_id).update_optional_key(key, item.text())
            self.__bids_folder.generate_participants_tsv()

    def ItemClicked(self, item):
        print("Current item changed")
        print("row: " + str(item.row()) + " column: " + str(item.column()))
        print("text: " + item.text())
        self.__previous_cell_text = item.text()