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
        MainWindow.resize(1212, 927)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.splitter = QtWidgets.QSplitter(parent=self.centralwidget)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.splitter.setObjectName("splitter")
        self.fileTreeView = QtWidgets.QTreeView(parent=self.splitter)
        self.fileTreeView.setMinimumSize(QtCore.QSize(320, 0))
        self.fileTreeView.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.fileTreeView.setObjectName("fileTreeView")
        self.tabWidget = QtWidgets.QTabWidget(parent=self.splitter)
        self.tabWidget.setEnabled(False)
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
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.tab)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.groupBox_2 = QtWidgets.QGroupBox(parent=self.tab)
        self.groupBox_2.setObjectName("groupBox_2")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox_2)
        self.verticalLayout.setObjectName("verticalLayout")
        self.SubjectLayout = QtWidgets.QHBoxLayout()
        self.SubjectLayout.setObjectName("SubjectLayout")
        self.AR_Subjectlabel = QtWidgets.QLabel(parent=self.groupBox_2)
        self.AR_Subjectlabel.setMinimumSize(QtCore.QSize(120, 0))
        self.AR_Subjectlabel.setMaximumSize(QtCore.QSize(120, 16777215))
        self.AR_Subjectlabel.setObjectName("AR_Subjectlabel")
        self.SubjectLayout.addWidget(self.AR_Subjectlabel)
        self.AR_SubjectComboBox = QtWidgets.QComboBox(parent=self.groupBox_2)
        self.AR_SubjectComboBox.setMinimumSize(QtCore.QSize(0, 0))
        self.AR_SubjectComboBox.setObjectName("AR_SubjectComboBox")
        self.SubjectLayout.addWidget(self.AR_SubjectComboBox)
        self.BidsValidatorPushButton = QtWidgets.QPushButton(parent=self.groupBox_2)
        self.BidsValidatorPushButton.setMinimumSize(QtCore.QSize(100, 0))
        self.BidsValidatorPushButton.setMaximumSize(QtCore.QSize(100, 16777215))
        self.BidsValidatorPushButton.setObjectName("BidsValidatorPushButton")
        self.SubjectLayout.addWidget(self.BidsValidatorPushButton)
        self.verticalLayout.addLayout(self.SubjectLayout)
        self.ModalityLayout = QtWidgets.QHBoxLayout()
        self.ModalityLayout.setObjectName("ModalityLayout")
        self.AR_ModalityLabel = QtWidgets.QLabel(parent=self.groupBox_2)
        self.AR_ModalityLabel.setMinimumSize(QtCore.QSize(120, 0))
        self.AR_ModalityLabel.setMaximumSize(QtCore.QSize(120, 16777215))
        self.AR_ModalityLabel.setObjectName("AR_ModalityLabel")
        self.ModalityLayout.addWidget(self.AR_ModalityLabel)
        self.AR_ModalityComboBox = QtWidgets.QComboBox(parent=self.groupBox_2)
        self.AR_ModalityComboBox.setMinimumSize(QtCore.QSize(0, 0))
        self.AR_ModalityComboBox.setObjectName("AR_ModalityComboBox")
        self.AR_ModalityComboBox.addItem("")
        self.AR_ModalityComboBox.addItem("")
        self.AR_ModalityComboBox.addItem("")
        self.AR_ModalityComboBox.addItem("")
        self.AR_ModalityComboBox.addItem("")
        self.AR_ModalityComboBox.addItem("")
        self.AR_ModalityComboBox.addItem("")
        self.AR_ModalityComboBox.addItem("")
        self.ModalityLayout.addWidget(self.AR_ModalityComboBox)
        self.verticalLayout.addLayout(self.ModalityLayout)
        self.BrowseLayout = QtWidgets.QHBoxLayout()
        self.BrowseLayout.setObjectName("BrowseLayout")
        self.AR_BrowseLineEdit = QtWidgets.QLineEdit(parent=self.groupBox_2)
        self.AR_BrowseLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.AR_BrowseLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_BrowseLineEdit.setObjectName("AR_BrowseLineEdit")
        self.BrowseLayout.addWidget(self.AR_BrowseLineEdit)
        self.AR_BrowsePushButton = QtWidgets.QPushButton(parent=self.groupBox_2)
        self.AR_BrowsePushButton.setMinimumSize(QtCore.QSize(150, 0))
        self.AR_BrowsePushButton.setMaximumSize(QtCore.QSize(150, 16777215))
        self.AR_BrowsePushButton.setObjectName("AR_BrowsePushButton")
        self.BrowseLayout.addWidget(self.AR_BrowsePushButton)
        self.AR_IsDicomFolderCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_2)
        self.AR_IsDicomFolderCheckBox.setObjectName("AR_IsDicomFolderCheckBox")
        self.BrowseLayout.addWidget(self.AR_IsDicomFolderCheckBox)
        self.verticalLayout.addLayout(self.BrowseLayout)
        self.EntitiesLayout1 = QtWidgets.QHBoxLayout()
        self.EntitiesLayout1.setObjectName("EntitiesLayout1")
        self.AR_SessionLabel = QtWidgets.QLabel(parent=self.groupBox_2)
        self.AR_SessionLabel.setMinimumSize(QtCore.QSize(120, 28))
        self.AR_SessionLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_SessionLabel.setObjectName("AR_SessionLabel")
        self.EntitiesLayout1.addWidget(self.AR_SessionLabel)
        self.AR_SessionComboBox = QtWidgets.QComboBox(parent=self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.AR_SessionComboBox.sizePolicy().hasHeightForWidth())
        self.AR_SessionComboBox.setSizePolicy(sizePolicy)
        self.AR_SessionComboBox.setMinimumSize(QtCore.QSize(0, 28))
        self.AR_SessionComboBox.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_SessionComboBox.setObjectName("AR_SessionComboBox")
        self.EntitiesLayout1.addWidget(self.AR_SessionComboBox)
        self.AR_TaskLabel = QtWidgets.QLabel(parent=self.groupBox_2)
        self.AR_TaskLabel.setMinimumSize(QtCore.QSize(120, 28))
        self.AR_TaskLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_TaskLabel.setObjectName("AR_TaskLabel")
        self.EntitiesLayout1.addWidget(self.AR_TaskLabel)
        self.AR_TaskComboBox = QtWidgets.QComboBox(parent=self.groupBox_2)
        self.AR_TaskComboBox.setMinimumSize(QtCore.QSize(0, 28))
        self.AR_TaskComboBox.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_TaskComboBox.setObjectName("AR_TaskComboBox")
        self.AR_TaskComboBox.addItem("")
        self.AR_TaskComboBox.addItem("")
        self.AR_TaskComboBox.addItem("")
        self.AR_TaskComboBox.addItem("")
        self.AR_TaskComboBox.addItem("")
        self.AR_TaskComboBox.addItem("")
        self.EntitiesLayout1.addWidget(self.AR_TaskComboBox)
        self.AR_ContrastAgentLabel = QtWidgets.QLabel(parent=self.groupBox_2)
        self.AR_ContrastAgentLabel.setMinimumSize(QtCore.QSize(120, 28))
        self.AR_ContrastAgentLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_ContrastAgentLabel.setObjectName("AR_ContrastAgentLabel")
        self.EntitiesLayout1.addWidget(self.AR_ContrastAgentLabel)
        self.AR_ContrastAgentLineEdit = QtWidgets.QLineEdit(parent=self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.AR_ContrastAgentLineEdit.sizePolicy().hasHeightForWidth())
        self.AR_ContrastAgentLineEdit.setSizePolicy(sizePolicy)
        self.AR_ContrastAgentLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.AR_ContrastAgentLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_ContrastAgentLineEdit.setObjectName("AR_ContrastAgentLineEdit")
        self.EntitiesLayout1.addWidget(self.AR_ContrastAgentLineEdit)
        self.verticalLayout.addLayout(self.EntitiesLayout1)
        self.EntitiesLayout2 = QtWidgets.QHBoxLayout()
        self.EntitiesLayout2.setObjectName("EntitiesLayout2")
        self.AR_AcquisitionLabel = QtWidgets.QLabel(parent=self.groupBox_2)
        self.AR_AcquisitionLabel.setMinimumSize(QtCore.QSize(120, 28))
        self.AR_AcquisitionLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_AcquisitionLabel.setObjectName("AR_AcquisitionLabel")
        self.EntitiesLayout2.addWidget(self.AR_AcquisitionLabel)
        self.AR_AcquisitionLineEdit = QtWidgets.QLineEdit(parent=self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.AR_AcquisitionLineEdit.sizePolicy().hasHeightForWidth())
        self.AR_AcquisitionLineEdit.setSizePolicy(sizePolicy)
        self.AR_AcquisitionLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.AR_AcquisitionLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_AcquisitionLineEdit.setObjectName("AR_AcquisitionLineEdit")
        self.EntitiesLayout2.addWidget(self.AR_AcquisitionLineEdit)
        self.AR_ReconstructionLabel = QtWidgets.QLabel(parent=self.groupBox_2)
        self.AR_ReconstructionLabel.setMinimumSize(QtCore.QSize(120, 28))
        self.AR_ReconstructionLabel.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_ReconstructionLabel.setObjectName("AR_ReconstructionLabel")
        self.EntitiesLayout2.addWidget(self.AR_ReconstructionLabel)
        self.AR_ReconstructionLineEdit = QtWidgets.QLineEdit(parent=self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.AR_ReconstructionLineEdit.sizePolicy().hasHeightForWidth())
        self.AR_ReconstructionLineEdit.setSizePolicy(sizePolicy)
        self.AR_ReconstructionLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.AR_ReconstructionLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_ReconstructionLineEdit.setObjectName("AR_ReconstructionLineEdit")
        self.EntitiesLayout2.addWidget(self.AR_ReconstructionLineEdit)
        self.verticalLayout.addLayout(self.EntitiesLayout2)
        self.AddRemoveFileLayout = QtWidgets.QHBoxLayout()
        self.AddRemoveFileLayout.setObjectName("AddRemoveFileLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.AddRemoveFileLayout.addItem(spacerItem)
        self.AR_AddPushButton = QtWidgets.QPushButton(parent=self.groupBox_2)
        self.AR_AddPushButton.setMinimumSize(QtCore.QSize(100, 0))
        self.AR_AddPushButton.setMaximumSize(QtCore.QSize(100, 16777215))
        self.AR_AddPushButton.setObjectName("AR_AddPushButton")
        self.AddRemoveFileLayout.addWidget(self.AR_AddPushButton)
        self.AR_RemovePushButton = QtWidgets.QPushButton(parent=self.groupBox_2)
        self.AR_RemovePushButton.setMinimumSize(QtCore.QSize(100, 0))
        self.AR_RemovePushButton.setMaximumSize(QtCore.QSize(100, 16777215))
        self.AR_RemovePushButton.setObjectName("AR_RemovePushButton")
        self.AddRemoveFileLayout.addWidget(self.AR_RemovePushButton)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.AddRemoveFileLayout.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.AddRemoveFileLayout)
        self.gridLayout_5.addWidget(self.groupBox_2, 0, 0, 1, 1)
        self.groupBox = QtWidgets.QGroupBox(parent=self.tab)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.IF_FileEditorLayout = QtWidgets.QHBoxLayout()
        self.IF_FileEditorLayout.setObjectName("IF_FileEditorLayout")
        self.gridLayout.addLayout(self.IF_FileEditorLayout, 0, 0, 1, 1)
        self.gridLayout_5.addWidget(self.groupBox, 1, 0, 1, 1)
        self.progressBar = QtWidgets.QProgressBar(parent=self.tab)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName("progressBar")
        self.gridLayout_5.addWidget(self.progressBar, 2, 0, 1, 1)
        self.StartImportLayout = QtWidgets.QHBoxLayout()
        self.StartImportLayout.setObjectName("StartImportLayout")
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.StartImportLayout.addItem(spacerItem2)
        self.StartImportPushButton = QtWidgets.QPushButton(parent=self.tab)
        self.StartImportPushButton.setObjectName("StartImportPushButton")
        self.StartImportLayout.addWidget(self.StartImportPushButton)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.StartImportLayout.addItem(spacerItem3)
        self.gridLayout_5.addLayout(self.StartImportLayout, 3, 0, 1, 1)
        self.tabWidget.addTab(self.tab, "")
        self.ImportSubjectsTab = QtWidgets.QWidget()
        self.ImportSubjectsTab.setObjectName("ImportSubjectsTab")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.ImportSubjectsTab)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.IS_ParseLabel = QtWidgets.QLabel(parent=self.ImportSubjectsTab)
        self.IS_ParseLabel.setObjectName("IS_ParseLabel")
        self.horizontalLayout_3.addWidget(self.IS_ParseLabel)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem4)
        self.IS_ParsePushButton = QtWidgets.QPushButton(parent=self.ImportSubjectsTab)
        self.IS_ParsePushButton.setObjectName("IS_ParsePushButton")
        self.horizontalLayout_3.addWidget(self.IS_ParsePushButton)
        self.gridLayout_3.addLayout(self.horizontalLayout_3, 0, 0, 1, 1)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.IS_SubjectListWidget = QtWidgets.QListWidget(parent=self.ImportSubjectsTab)
        self.IS_SubjectListWidget.setMinimumSize(QtCore.QSize(200, 0))
        self.IS_SubjectListWidget.setMaximumSize(QtCore.QSize(200, 16777215))
        self.IS_SubjectListWidget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.IS_SubjectListWidget.setObjectName("IS_SubjectListWidget")
        self.horizontalLayout_2.addWidget(self.IS_SubjectListWidget)
        self.IS_FileEditorLayout = QtWidgets.QHBoxLayout()
        self.IS_FileEditorLayout.setObjectName("IS_FileEditorLayout")
        self.horizontalLayout_2.addLayout(self.IS_FileEditorLayout)
        self.gridLayout_3.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)
        self.IS_progressBar = QtWidgets.QProgressBar(parent=self.ImportSubjectsTab)
        self.IS_progressBar.setProperty("value", 24)
        self.IS_progressBar.setObjectName("IS_progressBar")
        self.gridLayout_3.addWidget(self.IS_progressBar, 2, 0, 1, 1)
        self.IS_StartImportLayout = QtWidgets.QHBoxLayout()
        self.IS_StartImportLayout.setObjectName("IS_StartImportLayout")
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.IS_StartImportLayout.addItem(spacerItem5)
        self.IS_StartImportPushButton = QtWidgets.QPushButton(parent=self.ImportSubjectsTab)
        self.IS_StartImportPushButton.setObjectName("IS_StartImportPushButton")
        self.IS_StartImportLayout.addWidget(self.IS_StartImportPushButton)
        spacerItem6 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.IS_StartImportLayout.addItem(spacerItem6)
        self.gridLayout_3.addLayout(self.IS_StartImportLayout, 3, 0, 1, 1)
        self.tabWidget.addTab(self.ImportSubjectsTab, "")
        self.gridLayout_4.addWidget(self.splitter, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1212, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(parent=self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuOptions = QtWidgets.QMenu(parent=self.menubar)
        self.menuOptions.setObjectName("menuOptions")
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
        self.actionDatabase_Configuration = QtGui.QAction(parent=MainWindow)
        self.actionDatabase_Configuration.setObjectName("actionDatabase_Configuration")
        self.menuFile.addAction(self.actionNew_Bids_Dataset)
        self.menuFile.addAction(self.actionOpen_Bids_Dataset)
        self.menuFile.addAction(self.actionClose)
        self.menuOptions.addAction(self.actionDatabase_Configuration)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuOptions.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Bidsificator"))
        self.SubjectLineEdit.setPlaceholderText(_translate("MainWindow", "sub-<IDENTIFIER123>"))
        self.CreateSubjectPushButton.setText(_translate("MainWindow", "Create Subject"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.ParticipantsTab), _translate("MainWindow", "Participants"))
        self.groupBox_2.setTitle(_translate("MainWindow", "Add / Remove Files"))
        self.AR_Subjectlabel.setText(_translate("MainWindow", "Subject"))
        self.BidsValidatorPushButton.setText(_translate("MainWindow", "Bids Validator"))
        self.AR_ModalityLabel.setText(_translate("MainWindow", "Modality"))
        self.AR_ModalityComboBox.setItemText(0, _translate("MainWindow", "T1w (anat)"))
        self.AR_ModalityComboBox.setItemText(1, _translate("MainWindow", "T2w (anat)"))
        self.AR_ModalityComboBox.setItemText(2, _translate("MainWindow", "T1rho (anat)"))
        self.AR_ModalityComboBox.setItemText(3, _translate("MainWindow", "T2* (anat)"))
        self.AR_ModalityComboBox.setItemText(4, _translate("MainWindow", "FLAIR (anat)"))
        self.AR_ModalityComboBox.setItemText(5, _translate("MainWindow", "CT (anat)"))
        self.AR_ModalityComboBox.setItemText(6, _translate("MainWindow", "ieeg (ieeg)"))
        self.AR_ModalityComboBox.setItemText(7, _translate("MainWindow", "photo (ieeg)"))
        self.AR_BrowsePushButton.setText(_translate("MainWindow", "Browse File"))
        self.AR_IsDicomFolderCheckBox.setText(_translate("MainWindow", "Is DICOM Folder ?"))
        self.AR_SessionLabel.setText(_translate("MainWindow", "Session"))
        self.AR_TaskLabel.setText(_translate("MainWindow", "Task"))
        self.AR_TaskComboBox.setItemText(0, _translate("MainWindow", "Cognitiv"))
        self.AR_TaskComboBox.setItemText(1, _translate("MainWindow", "Seizure"))
        self.AR_TaskComboBox.setItemText(2, _translate("MainWindow", "Interictal"))
        self.AR_TaskComboBox.setItemText(3, _translate("MainWindow", "Stimulation"))
        self.AR_TaskComboBox.setItemText(4, _translate("MainWindow", "Sleep"))
        self.AR_TaskComboBox.setItemText(5, _translate("MainWindow", "Other"))
        self.AR_ContrastAgentLabel.setText(_translate("MainWindow", "Contrast Agent"))
        self.AR_AcquisitionLabel.setText(_translate("MainWindow", "Acquisition"))
        self.AR_ReconstructionLabel.setText(_translate("MainWindow", "Reconstruction"))
        self.AR_AddPushButton.setText(_translate("MainWindow", "Add"))
        self.AR_RemovePushButton.setText(_translate("MainWindow", "Remove"))
        self.groupBox.setTitle(_translate("MainWindow", "View / Edit Files"))
        self.StartImportPushButton.setText(_translate("MainWindow", "Start Import"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Import Files"))
        self.IS_ParseLabel.setText(_translate("MainWindow", "Parse Subjects Data : "))
        self.IS_ParsePushButton.setText(_translate("MainWindow", "Parse"))
        self.IS_StartImportPushButton.setText(_translate("MainWindow", "Start Import"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.ImportSubjectsTab), _translate("MainWindow", "Impots Subjects"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuOptions.setTitle(_translate("MainWindow", "Configuration"))
        self.actionLoad_Bids_Dataset_Folder.setText(_translate("MainWindow", "Load Bids Dataset Folder"))
        self.actionOpen_Bids_Dataset.setText(_translate("MainWindow", "Open Bids Dataset"))
        self.actionOpen_Multiple_Bids_Datasets.setText(_translate("MainWindow", "Open Multiple Bids Datasets"))
        self.actionNew_Bids_Dataset.setText(_translate("MainWindow", "New Bids Dataset"))
        self.actionClose.setText(_translate("MainWindow", "Close"))
        self.actionDatabase_Configuration.setText(_translate("MainWindow", "Database"))
from ..ui.PatientTableWidget import PatientTableWidget
