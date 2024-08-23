from PyQt6.QtWidgets import (
    QWidget,
    QMessageBox,
    QInputDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor

from ..core.BidsFolder import BidsFolder
from ..forms.FileEditor_ui import Ui_FileEditor

class FileEditor(QWidget, Ui_FileEditor):
    __item_memory = None
    __lock_for_update = False
    _subject_data = None

    def __init__(self):
        super(QWidget, self).__init__()
        self.setupUi(self)

        self.FileListWidget.itemClicked.connect(self.update_file_details)
        self.FileListWidget.itemSelectionChanged.connect(self.update_file_details)
        self.ModalityComboBox.currentIndexChanged.connect(self.update_userinterface_for_modality)
        self.TaskComboBox.currentTextChanged.connect(self.update_task_combobox_UI)

        self.EditPushButton.clicked.connect(self.toggle_edit_fields)
        self.CancelPushButton.clicked.connect(self.reset_edit_fields_from_memory)

        self.ModalityComboBox.currentTextChanged.connect(self.textEdited)
        self.SessionComboBox.currentTextChanged.connect(self.textEdited)
        self.TaskComboBox.currentTextChanged.connect(self.textEdited)
        self.ContrastAgentLineEdit.textEdited.connect(self.textEdited)
        self.ContrastAgentLineEdit.editingFinished.connect(self.editingFinished)
        self.AcquisitionLineEdit.textEdited.connect(self.textEdited)
        self.AcquisitionLineEdit.editingFinished.connect(self.editingFinished)
        self.ReconstructionLineEdit.textEdited.connect(self.textEdited)
        self.ReconstructionLineEdit.editingFinished.connect(self.editingFinished)
        self.PathLineEdit.textEdited.connect(self.textEdited)
        self.PathLineEdit.editingFinished.connect(self.editingFinished)

    def add_files_to_list(self, subject):
        self._subject_data = subject
        for file in subject["files"]:
            self.add_file_to_list(file["file_name"])

    def append_to_list(self, subject):
        if not self._subject_data:
            self._subject_data = subject
            self.add_file_to_list(subject["files"][0]["file_name"])
        else:
            if subject["subject_id"] != self._subject_data["subject_id"]:
                self.clear_file_list()
                self._subject_data = subject
                self._subject_data["files"].append(subject["files"][0])
                self.add_file_to_list(subject["files"][0]["file_name"])
                raise Exception("Subject ID mismatch, all previous files were removed")
            elif subject["files"][0] in self._subject_data["files"]:
                raise Exception("File already exists")
            else:
                self._subject_data["files"].append(subject["files"][0])
                self.add_file_to_list(subject["files"][0]["file_name"])

    def remove_selected_file_from_list(self):
        selectedIndexes = self.FileListWidget.selectedIndexes()
        if len(selectedIndexes) > 0:
            index = selectedIndexes[0].row()
            self.FileListWidget.takeItem(index)
            self._subject_data["files"].pop(index)
            self.update_file_details()

    def add_file_to_list(self, file_name):
        self.FileListWidget.addItem(file_name)

    def clear_file_list(self):
        self._subject_data = None
        self.FileListWidget.clear()

    def update_file_details(self):
        self.__lock_for_update = True
        selectedIndexes = self.FileListWidget.selectedIndexes()
        if len(selectedIndexes) > 0:
            file = self._subject_data["files"][selectedIndexes[0].row()]
            self.__item_memory = file
            if "(anat)" in file["modality"]:
                self.set_comboBox_text(self.ModalityComboBox, file["modality"])
                self.set_comboBox_text(self.SessionComboBox, str("ses-" + file["session"]))
                self.set_comboBox_text(self.TaskComboBox, "")
                self.ContrastAgentLineEdit.setText(file["contrast_agent"])
                self.AcquisitionLineEdit.setText(file["acquisition"])
                self.ReconstructionLineEdit.setText(file["reconstruction"])
                self.PathLineEdit.setText(file["file_path"])
            elif "(ieeg)" in file["modality"]:
                self.set_comboBox_text(self.ModalityComboBox, file["modality"])
                self.set_comboBox_text(self.SessionComboBox, str("ses-" + file["session"]))
                self.set_comboBox_text(self.TaskComboBox, file["task"])
                self.ContrastAgentLineEdit.setText("")
                self.AcquisitionLineEdit.setText(file["acquisition"])
                self.ReconstructionLineEdit.setText("")
                self.PathLineEdit.setText(file["file_path"])
            else:
                self.set_comboBox_text(self.ModalityComboBox, file["modality"])
                self.set_comboBox_text(self.SessionComboBox, str("ses-" + file["session"]))
                self.set_comboBox_text(self.TaskComboBox, file["task"])
                self.ContrastAgentLineEdit.setText(file["contrast_agent"])
                self.AcquisitionLineEdit.setText(file["acquisition"])
                self.ReconstructionLineEdit.setText(file["reconstruction"])
                self.PathLineEdit.setText(file["file_path"])
        else:
            self.set_comboBox_text(self.ModalityComboBox, "")
            self.set_comboBox_text(self.SessionComboBox, "")
            self.set_comboBox_text(self.TaskComboBox, "")
            self.ContrastAgentLineEdit.setText("")
            self.AcquisitionLineEdit.setText("")
            self.ReconstructionLineEdit.setText("")
            self.PathLineEdit.setText("")
        self.__lock_for_update = False

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
                self.TaskComboBox.currentTextChanged.connect(self.update_task_combobox_UI)

    def update_userinterface_for_modality(self):
        if "(anat)" in self.ModalityComboBox.currentText():
            #session
            self.SessionLabel.show()
            self.SessionComboBox.show()
            #task
            self.TaskLabel.hide()
            self.TaskComboBox.hide()
            #contrast
            self.ContrastAgentLabel.show()
            self.ContrastAgentLineEdit.show()
            #acquisition
            self.AcquisitionLabel.show()
            self.AcquisitionLineEdit.show()
            #reconstruction
            self.ReconstructionLabel.show()
            self.ReconstructionLineEdit.show()
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
        elif "photo (ieeg)" in self.ModalityComboBox.currentText():
            #session
            self.SessionLabel.show()
            self.SessionComboBox.show()
            #task
            self.TaskLabel.hide()
            self.TaskComboBox.hide()
            #contrast
            self.ContrastAgentLabel.hide()
            self.ContrastAgentLineEdit.hide()
            #acquisition
            self.AcquisitionLabel.show()
            self.AcquisitionLineEdit.show()
            #reconstruction
            self.ReconstructionLabel.hide()
            self.ReconstructionLineEdit.hide()
        else:
            print("Error : [__UpdateModalityUI] Modality not recognized")

    def toggle_edit_fields(self):
        newStatus = not self.AcquisitionLineEdit.isEnabled()
        if not newStatus and self.was_element_modified_UI():
            index2 = self.FileListWidget.currentIndex().row()
            file = {
                "file_name": self.FileListWidget.currentItem().text(),
                "file_path": self.PathLineEdit.text(),
                "modality": self.ModalityComboBox.currentText(),
                "task": self.TaskComboBox.currentText(),
                "session": self.SessionComboBox.currentText().removeprefix("ses-"),
                "contrast_agent": self.ContrastAgentLineEdit.text(),
                "acquisition": self.AcquisitionLineEdit.text(),
                "reconstruction": self.ReconstructionLineEdit.text()
            }
            self._subject_data["files"][index2] = file
            self.__item_memory = file

        newStatusLabel = "Editing" if newStatus else "Edit"
        self.EditPushButton.setText(newStatusLabel)
        self.FileListWidget.setEnabled(not newStatus)

        self.ModalityComboBox.setEnabled(newStatus)
        self.SessionComboBox.setEnabled(newStatus)
        self.TaskComboBox.setEnabled(newStatus)
        self.ContrastAgentLineEdit.setEnabled(newStatus)
        self.AcquisitionLineEdit.setEnabled(newStatus)
        self.ReconstructionLineEdit.setEnabled(newStatus)
        self.PathLineEdit.setEnabled(newStatus)

    def reset_edit_fields_from_memory(self):
        self.set_comboBox_text(self.ModalityComboBox, self.__item_memory["modality"])
        self.set_comboBox_text(self.SessionComboBox, str("ses-" + self.__item_memory["session"]))
        self.set_comboBox_text(self.TaskComboBox, self.__item_memory["task"])
        self.ContrastAgentLineEdit.setText(self.__item_memory['contrast_agent'])
        self.AcquisitionLineEdit.setText(self.__item_memory['acquisition'])
        self.ReconstructionLineEdit.setText(self.__item_memory['reconstruction'])
        self.PathLineEdit.setText(self.__item_memory['file_path'])
        #Clear focus to trigger editingFinished
        self.ModalityComboBox.clearFocus()
        self.SessionComboBox.clearFocus()
        self.TaskComboBox.clearFocus()
        self.ContrastAgentLineEdit.clearFocus()
        self.AcquisitionLineEdit.clearFocus()
        self.ReconstructionLineEdit.clearFocus()
        self.PathLineEdit.clearFocus()

    def set_comboBox_text(self, comboBox, text):
        index = comboBox.findText(text)
        if index >= 0:
            comboBox.setCurrentIndex(index)
        else:
            comboBox.setCurrentIndex(-1)

        comboBox.clearFocus()

    def was_element_modified_UI(self):
        if self.FileListWidget.currentItem() is None:
            return False
        if not self.__item_memory:
            return False

        file = {
            "file_name": self.FileListWidget.currentItem().text(),
            "file_path": self.PathLineEdit.text(),
            "modality": self.ModalityComboBox.currentText(),
            "task": self.TaskComboBox.currentText(),
            "session": self.SessionComboBox.currentText().removeprefix("ses-"),
            "contrast_agent": self.ContrastAgentLineEdit.text(),
            "acquisition": self.AcquisitionLineEdit.text(),
            "reconstruction": self.ReconstructionLineEdit.text()
        }

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

    def textEdited(self, text):
        #print("Text edited : " + text)
        if not self.__lock_for_update:
            self.CancelPushButton.setEnabled(self.was_element_modified_UI())

    def editingFinished(self):
        #print("Editing finished")
        if not self.__lock_for_update:
            self.CancelPushButton.setEnabled(self.was_element_modified_UI())
