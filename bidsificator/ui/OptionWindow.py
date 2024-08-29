import re
from PyQt6.QtWidgets import (
    QWidget,
    QMessageBox,
    QFileDialog,
    QInputDialog,
)
from PyQt6.QtCore import QStandardPaths

from ..core.OptionFile import OptionFile
from ..forms.OptionWindow_ui import Ui_OptionsForm

class OptionWindow(QWidget, Ui_OptionsForm):
    def __init__(self):
        super(QWidget, self).__init__()
        self.setupUi(self)
        self.options = OptionFile('bidsificator/config/config.yaml')
        #==
        self.separatedDbCheckBox.stateChanged.connect(self.SeparatedDbCheckBox_stateChanged)
        self.AnatDbBrowse.clicked.connect(self.AnatDbBrowse_clicked)
        self.AnatDbLineEdit.editingFinished.connect(self.AnatDbBrowse_editingFinished)
        self.FuncDbBrowse.clicked.connect(self.FuncDbBrowse_clicked)
        self.FuncDbLineEdit.editingFinished.connect(self.FuncDbBrowse_editingFinished)
        self.SubPatternLineEdit.editingFinished.connect(self.SubPatternLineEdit_editingFinished)
        self.listWidget.clicked.connect(self.on_ListWidget_clicked)
        self.AddDataTypePushButton.clicked.connect(self.AddDataTypePushButton_clicked)
        self.RemoveDataTypePushButton.clicked.connect(self.RemoveDataTypePushButton_clicked)
        self.DescriptionLineEdit.editingFinished.connect(self.DescriptionLineEdit_editingFinished)
        self.DirectoryLineEdit.editingFinished.connect(self.DirectoryLineEdit_editingFinished)
        self.FileExtLineEdit.editingFinished.connect(self.FileExtLineEdit_editingFinished)
        self.OkPushButton.clicked.connect(self.OkPushButton_clicked)
        self.CancelPushButton.clicked.connect(self.close)
        #== Init display for db options
        show = self.options.db_path['anatomical'] != self.options.db_path['functional']
        self.separatedDbCheckBox.setChecked(show)
        self.FuncLabel.setVisible(show)
        self.FuncDbLineEdit.setVisible(show)
        self.FuncDbBrowse.setVisible(show)
        self.AnatDbLineEdit.setText(self.options.db_path['anatomical'])
        self.FuncDbLineEdit.setText(self.options.db_path['functional'])
        self.SubPatternLineEdit.setText(self.options.subject_pattern)
        for data_type in self.options.data_types:
            self.listWidget.addItem(data_type)

    def SeparatedDbCheckBox_stateChanged(self):
        show = self.separatedDbCheckBox.isChecked()
        if not show:
            self.FuncDbLineEdit.setText(self.AnatDbLineEdit.text())
        self.FuncLabel.setVisible(show)
        self.FuncDbLineEdit.setVisible(show)
        self.FuncDbBrowse.setVisible(show)

    def AnatDbBrowse_clicked(self):
        db_path = QFileDialog.getExistingDirectory(self, "Select anatomical database directory", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        if db_path:
            self.AnatDbLineEdit.setText(db_path)

    def AnatDbBrowse_editingFinished(self):
        self.options.db_path['anatomical'] = self.AnatDbLineEdit.text()

    def FuncDbBrowse_clicked(self):
        db_path = QFileDialog.getExistingDirectory(self, "Select functional database directory", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        if db_path:
            self.FuncDbLineEdit.setText(db_path)

    def FuncDbBrowse_editingFinished(self):
        self.options.db_path['functional'] = self.FuncDbLineEdit.text()

    def SubPatternLineEdit_editingFinished(self):
        self.options.subject_pattern = self.SubPatternLineEdit.text()

    def on_ListWidget_clicked(self):
        selected_item = self.listWidget.currentItem().text()
        self.DescriptionLineEdit.setText(self.options.data_types[selected_item]['description'])
        self.DirectoryLineEdit.setText(self.options.data_types[selected_item]['directory'])
        self.FileExtLineEdit.setText(', '.join(self.options.data_types[selected_item]['file_extensions']))

    def AddDataTypePushButton_clicked(self):
        data_type = QInputDialog.getText(self, "Data type Name", "Enter a name for the data type")[0]
        self.options.data_types[data_type] = {
            'description': '',
            'directory': '',
            'file_extensions': []
        }
        self.listWidget.addItem(data_type)

    def RemoveDataTypePushButton_clicked(self):
        if self.listWidget.currentRow() == -1:
            return
        selected_item = self.listWidget.currentItem().text()
        self.options.data_types.pop(selected_item)
        self.listWidget.takeItem(self.listWidget.currentRow())

    def DescriptionLineEdit_editingFinished(self):
        selected_item = self.listWidget.currentItem().text()
        self.options.data_types[selected_item]['description'] = self.DescriptionLineEdit.text()

    def DirectoryLineEdit_editingFinished(self):
        selected_item = self.listWidget.currentItem().text()
        self.options.data_types[selected_item]['directory'] = self.DirectoryLineEdit.text()

    def FileExtLineEdit_editingFinished(self):
        if not self.is_valid_extensions(self.FileExtLineEdit.text()):
            QMessageBox.critical(self, 'Invalid file extensions', 'Please enter valid file extensions separated by ", ".')
            return

        selected_item = self.listWidget.currentItem().text()
        self.options.data_types[selected_item]['file_extensions'] = self.FileExtLineEdit.text().split(', ')

    def OkPushButton_clicked(self):
        # trigger the editingFinished signals to save the last changes
        self.setFocus()
        self.options.save()
        self.close()

    def is_valid_extensions(self, input_string):
        # Regular expression to match valid file extensions separated by ", "
        pattern = r'^(\.[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)?)(, \.[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)?)*$'
        return bool(re.match(pattern, input_string))
