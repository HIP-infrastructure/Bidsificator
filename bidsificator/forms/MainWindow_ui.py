# Form implementation generated from reading ui file '/Users/florian/Documents/Arbeit/CHUV/Repository/Python/Bidsificator/bidsificator/forms/MainWindow.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1000, 859)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.fileTreeView = QtWidgets.QTreeView(parent=self.centralwidget)
        self.fileTreeView.setMinimumSize(QtCore.QSize(320, 0))
        self.fileTreeView.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.fileTreeView.setObjectName("fileTreeView")
        self.gridLayout_3.addWidget(self.fileTreeView, 0, 0, 1, 1)
        self.tabWidget = QtWidgets.QTabWidget(parent=self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.ParticipantsTab = QtWidgets.QWidget()
        self.ParticipantsTab.setObjectName("ParticipantsTab")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.ParticipantsTab)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.CreateSubjectLayout = QtWidgets.QHBoxLayout()
        self.CreateSubjectLayout.setObjectName("CreateSubjectLayout")
        self.SubjectLineEdit = QtWidgets.QLineEdit(parent=self.ParticipantsTab)
        self.SubjectLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.SubjectLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.SubjectLineEdit.setInputMask("")
        self.SubjectLineEdit.setText("")
        self.SubjectLineEdit.setMaxLength(32767)
        self.SubjectLineEdit.setCursorPosition(0)
        self.SubjectLineEdit.setCursorMoveStyle(QtCore.Qt.CursorMoveStyle.VisualMoveStyle)
        self.SubjectLineEdit.setObjectName("SubjectLineEdit")
        self.CreateSubjectLayout.addWidget(self.SubjectLineEdit)
        self.CreateSubjectPushButton = QtWidgets.QPushButton(parent=self.ParticipantsTab)
        self.CreateSubjectPushButton.setMinimumSize(QtCore.QSize(150, 0))
        self.CreateSubjectPushButton.setMaximumSize(QtCore.QSize(150, 16777215))
        self.CreateSubjectPushButton.setObjectName("CreateSubjectPushButton")
        self.CreateSubjectLayout.addWidget(self.CreateSubjectPushButton)
        self.gridLayout_2.addLayout(self.CreateSubjectLayout, 0, 0, 1, 1)
        self.tableWidget = PatientTableWidget(parent=self.ParticipantsTab)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        self.gridLayout_2.addWidget(self.tableWidget, 1, 0, 1, 1)
        self.tabWidget.addTab(self.ParticipantsTab, "")
        self.ImportTab = QtWidgets.QWidget()
        self.ImportTab.setObjectName("ImportTab")
        self.gridLayout = QtWidgets.QGridLayout(self.ImportTab)
        self.gridLayout.setObjectName("gridLayout")
        self.SubjectLayout = QtWidgets.QHBoxLayout()
        self.SubjectLayout.setObjectName("SubjectLayout")
        self.Subjectlabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.Subjectlabel.setMinimumSize(QtCore.QSize(120, 0))
        self.Subjectlabel.setMaximumSize(QtCore.QSize(120, 16777215))
        self.Subjectlabel.setObjectName("Subjectlabel")
        self.SubjectLayout.addWidget(self.Subjectlabel)
        self.SubjectComboBox = QtWidgets.QComboBox(parent=self.ImportTab)
        self.SubjectComboBox.setMinimumSize(QtCore.QSize(0, 0))
        self.SubjectComboBox.setObjectName("SubjectComboBox")
        self.SubjectLayout.addWidget(self.SubjectComboBox)
        self.BidsValidatorPushButton = QtWidgets.QPushButton(parent=self.ImportTab)
        self.BidsValidatorPushButton.setMinimumSize(QtCore.QSize(100, 0))
        self.BidsValidatorPushButton.setMaximumSize(QtCore.QSize(100, 16777215))
        self.BidsValidatorPushButton.setObjectName("BidsValidatorPushButton")
        self.SubjectLayout.addWidget(self.BidsValidatorPushButton)
        self.gridLayout.addLayout(self.SubjectLayout, 0, 0, 1, 1)
        self.AddRemoveFileLayout = QtWidgets.QHBoxLayout()
        self.AddRemoveFileLayout.setObjectName("AddRemoveFileLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.AddRemoveFileLayout.addItem(spacerItem)
        self.AddPushButton = QtWidgets.QPushButton(parent=self.ImportTab)
        self.AddPushButton.setMinimumSize(QtCore.QSize(100, 0))
        self.AddPushButton.setMaximumSize(QtCore.QSize(100, 16777215))
        self.AddPushButton.setObjectName("AddPushButton")
        self.AddRemoveFileLayout.addWidget(self.AddPushButton)
        self.RemovePushButton = QtWidgets.QPushButton(parent=self.ImportTab)
        self.RemovePushButton.setMinimumSize(QtCore.QSize(100, 0))
        self.RemovePushButton.setMaximumSize(QtCore.QSize(100, 16777215))
        self.RemovePushButton.setObjectName("RemovePushButton")
        self.AddRemoveFileLayout.addWidget(self.RemovePushButton)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.AddRemoveFileLayout.addItem(spacerItem1)
        self.gridLayout.addLayout(self.AddRemoveFileLayout, 5, 0, 1, 1)
        self.InfoLayout = QtWidgets.QHBoxLayout()
        self.InfoLayout.setObjectName("InfoLayout")
        self.fileListWidget = QtWidgets.QListWidget(parent=self.ImportTab)
        self.fileListWidget.setMinimumSize(QtCore.QSize(300, 0))
        self.fileListWidget.setMaximumSize(QtCore.QSize(300, 16777215))
        self.fileListWidget.setObjectName("fileListWidget")
        self.InfoLayout.addWidget(self.fileListWidget)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(spacerItem2)
        self.SessionLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.SessionLabel.setMinimumSize(QtCore.QSize(0, 0))
        self.SessionLabel.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.SessionLabel.setObjectName("SessionLabel")
        self.verticalLayout.addWidget(self.SessionLabel)
        self.TaskLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.TaskLabel.setMinimumSize(QtCore.QSize(0, 0))
        self.TaskLabel.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.TaskLabel.setObjectName("TaskLabel")
        self.verticalLayout.addWidget(self.TaskLabel)
        self.ContrastAgentLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.ContrastAgentLabel.setMinimumSize(QtCore.QSize(0, 0))
        self.ContrastAgentLabel.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.ContrastAgentLabel.setObjectName("ContrastAgentLabel")
        self.verticalLayout.addWidget(self.ContrastAgentLabel)
        self.AcquisitionLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.AcquisitionLabel.setMinimumSize(QtCore.QSize(0, 0))
        self.AcquisitionLabel.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.AcquisitionLabel.setObjectName("AcquisitionLabel")
        self.verticalLayout.addWidget(self.AcquisitionLabel)
        self.ReconstructionLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.ReconstructionLabel.setMinimumSize(QtCore.QSize(0, 0))
        self.ReconstructionLabel.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.ReconstructionLabel.setObjectName("ReconstructionLabel")
        self.verticalLayout.addWidget(self.ReconstructionLabel)
        self.FilePathLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.FilePathLabel.setMinimumSize(QtCore.QSize(0, 0))
        self.FilePathLabel.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.FilePathLabel.setWordWrap(True)
        self.FilePathLabel.setObjectName("FilePathLabel")
        self.verticalLayout.addWidget(self.FilePathLabel)
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(spacerItem3)
        self.InfoLayout.addLayout(self.verticalLayout)
        self.gridLayout.addLayout(self.InfoLayout, 6, 0, 1, 1)
        self.BrowseLayout = QtWidgets.QHBoxLayout()
        self.BrowseLayout.setObjectName("BrowseLayout")
        self.BrowseLineEdit = QtWidgets.QLineEdit(parent=self.ImportTab)
        self.BrowseLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.BrowseLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.BrowseLineEdit.setObjectName("BrowseLineEdit")
        self.BrowseLayout.addWidget(self.BrowseLineEdit)
        self.BrowsePushButton = QtWidgets.QPushButton(parent=self.ImportTab)
        self.BrowsePushButton.setMinimumSize(QtCore.QSize(150, 0))
        self.BrowsePushButton.setMaximumSize(QtCore.QSize(150, 16777215))
        self.BrowsePushButton.setObjectName("BrowsePushButton")
        self.BrowseLayout.addWidget(self.BrowsePushButton)
        self.IsDicomFolderCheckBox = QtWidgets.QCheckBox(parent=self.ImportTab)
        self.IsDicomFolderCheckBox.setObjectName("IsDicomFolderCheckBox")
        self.BrowseLayout.addWidget(self.IsDicomFolderCheckBox)
        self.gridLayout.addLayout(self.BrowseLayout, 1, 0, 1, 1)
        self.StartImportLayout = QtWidgets.QHBoxLayout()
        self.StartImportLayout.setObjectName("StartImportLayout")
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.StartImportLayout.addItem(spacerItem4)
        self.StartImportPushButton = QtWidgets.QPushButton(parent=self.ImportTab)
        self.StartImportPushButton.setObjectName("StartImportPushButton")
        self.StartImportLayout.addWidget(self.StartImportPushButton)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.StartImportLayout.addItem(spacerItem5)
        self.gridLayout.addLayout(self.StartImportLayout, 8, 0, 1, 1)
        self.progressBar = QtWidgets.QProgressBar(parent=self.ImportTab)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName("progressBar")
        self.gridLayout.addWidget(self.progressBar, 7, 0, 1, 1)
        self.EntitiesLayout2 = QtWidgets.QHBoxLayout()
        self.EntitiesLayout2.setObjectName("EntitiesLayout2")
        self.acquisitionLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.acquisitionLabel.setMinimumSize(QtCore.QSize(120, 28))
        self.acquisitionLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        self.acquisitionLabel.setObjectName("acquisitionLabel")
        self.EntitiesLayout2.addWidget(self.acquisitionLabel)
        self.acquisitionLineEdit = QtWidgets.QLineEdit(parent=self.ImportTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.acquisitionLineEdit.sizePolicy().hasHeightForWidth())
        self.acquisitionLineEdit.setSizePolicy(sizePolicy)
        self.acquisitionLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.acquisitionLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.acquisitionLineEdit.setObjectName("acquisitionLineEdit")
        self.EntitiesLayout2.addWidget(self.acquisitionLineEdit)
        self.reconstructionLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.reconstructionLabel.setMinimumSize(QtCore.QSize(120, 28))
        self.reconstructionLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        self.reconstructionLabel.setObjectName("reconstructionLabel")
        self.EntitiesLayout2.addWidget(self.reconstructionLabel)
        self.reconstructionLineEdit = QtWidgets.QLineEdit(parent=self.ImportTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.reconstructionLineEdit.sizePolicy().hasHeightForWidth())
        self.reconstructionLineEdit.setSizePolicy(sizePolicy)
        self.reconstructionLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.reconstructionLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.reconstructionLineEdit.setObjectName("reconstructionLineEdit")
        self.EntitiesLayout2.addWidget(self.reconstructionLineEdit)
        self.gridLayout.addLayout(self.EntitiesLayout2, 4, 0, 1, 1)
        self.EntitiesLayout1 = QtWidgets.QHBoxLayout()
        self.EntitiesLayout1.setObjectName("EntitiesLayout1")
        self.sessionLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.sessionLabel.setMinimumSize(QtCore.QSize(120, 28))
        self.sessionLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        self.sessionLabel.setObjectName("sessionLabel")
        self.EntitiesLayout1.addWidget(self.sessionLabel)
        self.sessionComboBox = QtWidgets.QComboBox(parent=self.ImportTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sessionComboBox.sizePolicy().hasHeightForWidth())
        self.sessionComboBox.setSizePolicy(sizePolicy)
        self.sessionComboBox.setMinimumSize(QtCore.QSize(0, 28))
        self.sessionComboBox.setMaximumSize(QtCore.QSize(16777215, 28))
        self.sessionComboBox.setObjectName("sessionComboBox")
        self.EntitiesLayout1.addWidget(self.sessionComboBox)
        self.taskLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.taskLabel.setMinimumSize(QtCore.QSize(120, 28))
        self.taskLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        self.taskLabel.setObjectName("taskLabel")
        self.EntitiesLayout1.addWidget(self.taskLabel)
        self.taskLineEdit = QtWidgets.QLineEdit(parent=self.ImportTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.taskLineEdit.sizePolicy().hasHeightForWidth())
        self.taskLineEdit.setSizePolicy(sizePolicy)
        self.taskLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.taskLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.taskLineEdit.setObjectName("taskLineEdit")
        self.EntitiesLayout1.addWidget(self.taskLineEdit)
        self.contrastAgentLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.contrastAgentLabel.setMinimumSize(QtCore.QSize(120, 28))
        self.contrastAgentLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        self.contrastAgentLabel.setObjectName("contrastAgentLabel")
        self.EntitiesLayout1.addWidget(self.contrastAgentLabel)
        self.contrastAgentLineEdit = QtWidgets.QLineEdit(parent=self.ImportTab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.contrastAgentLineEdit.sizePolicy().hasHeightForWidth())
        self.contrastAgentLineEdit.setSizePolicy(sizePolicy)
        self.contrastAgentLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.contrastAgentLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.contrastAgentLineEdit.setObjectName("contrastAgentLineEdit")
        self.EntitiesLayout1.addWidget(self.contrastAgentLineEdit)
        self.gridLayout.addLayout(self.EntitiesLayout1, 3, 0, 1, 1)
        self.ModalityLayout = QtWidgets.QHBoxLayout()
        self.ModalityLayout.setObjectName("ModalityLayout")
        self.ModalityLabel = QtWidgets.QLabel(parent=self.ImportTab)
        self.ModalityLabel.setMinimumSize(QtCore.QSize(120, 0))
        self.ModalityLabel.setMaximumSize(QtCore.QSize(120, 16777215))
        self.ModalityLabel.setObjectName("ModalityLabel")
        self.ModalityLayout.addWidget(self.ModalityLabel)
        self.ModlalityComboBox = QtWidgets.QComboBox(parent=self.ImportTab)
        self.ModlalityComboBox.setMinimumSize(QtCore.QSize(0, 0))
        self.ModlalityComboBox.setObjectName("ModlalityComboBox")
        self.ModlalityComboBox.addItem("")
        self.ModlalityComboBox.addItem("")
        self.ModlalityComboBox.addItem("")
        self.ModlalityComboBox.addItem("")
        self.ModlalityComboBox.addItem("")
        self.ModlalityComboBox.addItem("")
        self.ModlalityComboBox.addItem("")
        self.ModlalityComboBox.addItem("")
        self.ModalityLayout.addWidget(self.ModlalityComboBox)
        self.gridLayout.addLayout(self.ModalityLayout, 2, 0, 1, 1)
        self.tabWidget.addTab(self.ImportTab, "")
        self.gridLayout_3.addWidget(self.tabWidget, 0, 1, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1000, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(parent=self.menubar)
        self.menuFile.setObjectName("menuFile")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionLoad_Bids_Dataset_Folder = QtGui.QAction(parent=MainWindow)
        self.actionLoad_Bids_Dataset_Folder.setObjectName("actionLoad_Bids_Dataset_Folder")
        self.actionOpen_Bids_Dataset = QtGui.QAction(parent=MainWindow)
        self.actionOpen_Bids_Dataset.setObjectName("actionOpen_Bids_Dataset")
        self.actionOpen_Multiple_Bids_Datasets = QtGui.QAction(parent=MainWindow)
        self.actionOpen_Multiple_Bids_Datasets.setObjectName("actionOpen_Multiple_Bids_Datasets")
        self.actionNew_Bids_Dataset = QtGui.QAction(parent=MainWindow)
        self.actionNew_Bids_Dataset.setObjectName("actionNew_Bids_Dataset")
        self.actionClose = QtGui.QAction(parent=MainWindow)
        self.actionClose.setObjectName("actionClose")
        self.menuFile.addAction(self.actionNew_Bids_Dataset)
        self.menuFile.addAction(self.actionOpen_Bids_Dataset)
        self.menuFile.addAction(self.actionClose)
        self.menubar.addAction(self.menuFile.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Bidsificator"))
        self.SubjectLineEdit.setPlaceholderText(_translate("MainWindow", "sub-<IDENTIFIER123>"))
        self.CreateSubjectPushButton.setText(_translate("MainWindow", "Create Subject"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.ParticipantsTab), _translate("MainWindow", "Participants"))
        self.Subjectlabel.setText(_translate("MainWindow", "Subject"))
        self.BidsValidatorPushButton.setText(_translate("MainWindow", "Bids Validator"))
        self.AddPushButton.setText(_translate("MainWindow", "Add"))
        self.RemovePushButton.setText(_translate("MainWindow", "Remove"))
        self.SessionLabel.setText(_translate("MainWindow", "Session :"))
        self.TaskLabel.setText(_translate("MainWindow", "Task :"))
        self.ContrastAgentLabel.setText(_translate("MainWindow", "Contrast Agent :"))
        self.AcquisitionLabel.setText(_translate("MainWindow", "Acquisition :"))
        self.ReconstructionLabel.setText(_translate("MainWindow", "Reconstruction :"))
        self.FilePathLabel.setText(_translate("MainWindow", "Path :"))
        self.BrowsePushButton.setText(_translate("MainWindow", "Browse File"))
        self.IsDicomFolderCheckBox.setText(_translate("MainWindow", "Is DICOM Folder ?"))
        self.StartImportPushButton.setText(_translate("MainWindow", "Start Import"))
        self.acquisitionLabel.setText(_translate("MainWindow", "Acquisition"))
        self.reconstructionLabel.setText(_translate("MainWindow", "Reconstruction"))
        self.sessionLabel.setText(_translate("MainWindow", "Session"))
        self.taskLabel.setText(_translate("MainWindow", "Task"))
        self.contrastAgentLabel.setText(_translate("MainWindow", "Contrast Agent"))
        self.ModalityLabel.setText(_translate("MainWindow", "Modality"))
        self.ModlalityComboBox.setItemText(0, _translate("MainWindow", "T1w (anat)"))
        self.ModlalityComboBox.setItemText(1, _translate("MainWindow", "T2w (anat)"))
        self.ModlalityComboBox.setItemText(2, _translate("MainWindow", "T1rho (anat)"))
        self.ModlalityComboBox.setItemText(3, _translate("MainWindow", "T2start (anat)"))
        self.ModlalityComboBox.setItemText(4, _translate("MainWindow", "FLAIR (anat)"))
        self.ModlalityComboBox.setItemText(5, _translate("MainWindow", "ct (anat)"))
        self.ModlalityComboBox.setItemText(6, _translate("MainWindow", "ieeg (ieeg)"))
        self.ModlalityComboBox.setItemText(7, _translate("MainWindow", "photo (ieeg)"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.ImportTab), _translate("MainWindow", "Import Files"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.actionLoad_Bids_Dataset_Folder.setText(_translate("MainWindow", "Load Bids Dataset Folder"))
        self.actionOpen_Bids_Dataset.setText(_translate("MainWindow", "Open Bids Dataset"))
        self.actionOpen_Multiple_Bids_Datasets.setText(_translate("MainWindow", "Open Multiple Bids Datasets"))
        self.actionNew_Bids_Dataset.setText(_translate("MainWindow", "New Bids Dataset"))
        self.actionClose.setText(_translate("MainWindow", "Close"))
from ui.PatientTableWidget import PatientTableWidget
