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
        MainWindow.resize(1105, 859)
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
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.ImportTab)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.groupBox_2 = QtWidgets.QGroupBox(parent=self.ImportTab)
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
        self.AR_TaskLineEdit = QtWidgets.QLineEdit(parent=self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.AR_TaskLineEdit.sizePolicy().hasHeightForWidth())
        self.AR_TaskLineEdit.setSizePolicy(sizePolicy)
        self.AR_TaskLineEdit.setMinimumSize(QtCore.QSize(0, 28))
        self.AR_TaskLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.AR_TaskLineEdit.setObjectName("AR_TaskLineEdit")
        self.EntitiesLayout1.addWidget(self.AR_TaskLineEdit)
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
        self.verticalLayout_2.addWidget(self.groupBox_2)
        self.groupBox = QtWidgets.QGroupBox(parent=self.ImportTab)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.VE_TaskLineEdit = QtWidgets.QLineEdit(parent=self.groupBox)
        self.VE_TaskLineEdit.setEnabled(False)
        self.VE_TaskLineEdit.setMinimumSize(QtCore.QSize(210, 28))
        self.VE_TaskLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.VE_TaskLineEdit.setObjectName("VE_TaskLineEdit")
        self.gridLayout.addWidget(self.VE_TaskLineEdit, 3, 3, 1, 1)
        self.VE_SessionLabel = QtWidgets.QLabel(parent=self.groupBox)
        self.VE_SessionLabel.setMinimumSize(QtCore.QSize(110, 0))
        self.VE_SessionLabel.setMaximumSize(QtCore.QSize(110, 16777215))
        self.VE_SessionLabel.setObjectName("VE_SessionLabel")
        self.gridLayout.addWidget(self.VE_SessionLabel, 2, 1, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(20, 79, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.gridLayout.addItem(spacerItem2, 9, 3, 1, 1)
        self.VE_FileListWidget = QtWidgets.QListWidget(parent=self.groupBox)
        self.VE_FileListWidget.setMinimumSize(QtCore.QSize(300, 0))
        self.VE_FileListWidget.setMaximumSize(QtCore.QSize(300, 16777215))
        self.VE_FileListWidget.setObjectName("VE_FileListWidget")
        self.gridLayout.addWidget(self.VE_FileListWidget, 0, 0, 10, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem3)
        self.VE_EditPushButton = QtWidgets.QPushButton(parent=self.groupBox)
        self.VE_EditPushButton.setMinimumSize(QtCore.QSize(100, 0))
        self.VE_EditPushButton.setMaximumSize(QtCore.QSize(100, 16777215))
        self.VE_EditPushButton.setObjectName("VE_EditPushButton")
        self.horizontalLayout.addWidget(self.VE_EditPushButton)
        self.VE_CancelPushButton = QtWidgets.QPushButton(parent=self.groupBox)
        self.VE_CancelPushButton.setEnabled(False)
        self.VE_CancelPushButton.setMinimumSize(QtCore.QSize(100, 0))
        self.VE_CancelPushButton.setMaximumSize(QtCore.QSize(100, 16777215))
        self.VE_CancelPushButton.setObjectName("VE_CancelPushButton")
        self.horizontalLayout.addWidget(self.VE_CancelPushButton)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem4)
        self.gridLayout.addLayout(self.horizontalLayout, 8, 1, 1, 3)
        spacerItem5 = QtWidgets.QSpacerItem(20, 80, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.gridLayout.addItem(spacerItem5, 0, 3, 1, 1)
        self.VE_TaskLabel = QtWidgets.QLabel(parent=self.groupBox)
        self.VE_TaskLabel.setMinimumSize(QtCore.QSize(110, 0))
        self.VE_TaskLabel.setMaximumSize(QtCore.QSize(110, 16777215))
        self.VE_TaskLabel.setObjectName("VE_TaskLabel")
        self.gridLayout.addWidget(self.VE_TaskLabel, 3, 1, 1, 1)
        self.VE_PathLineEdit = QtWidgets.QLineEdit(parent=self.groupBox)
        self.VE_PathLineEdit.setEnabled(False)
        self.VE_PathLineEdit.setMinimumSize(QtCore.QSize(210, 28))
        self.VE_PathLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.VE_PathLineEdit.setObjectName("VE_PathLineEdit")
        self.gridLayout.addWidget(self.VE_PathLineEdit, 7, 3, 1, 1)
        self.VE_AcquisitionLineEdit = QtWidgets.QLineEdit(parent=self.groupBox)
        self.VE_AcquisitionLineEdit.setEnabled(False)
        self.VE_AcquisitionLineEdit.setMinimumSize(QtCore.QSize(210, 28))
        self.VE_AcquisitionLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.VE_AcquisitionLineEdit.setObjectName("VE_AcquisitionLineEdit")
        self.gridLayout.addWidget(self.VE_AcquisitionLineEdit, 5, 3, 1, 1)
        self.VE_ReconstructionLabel = QtWidgets.QLabel(parent=self.groupBox)
        self.VE_ReconstructionLabel.setMinimumSize(QtCore.QSize(110, 0))
        self.VE_ReconstructionLabel.setMaximumSize(QtCore.QSize(110, 16777215))
        self.VE_ReconstructionLabel.setObjectName("VE_ReconstructionLabel")
        self.gridLayout.addWidget(self.VE_ReconstructionLabel, 6, 1, 1, 1)
        self.VE_ContrastAgentLineEdit = QtWidgets.QLineEdit(parent=self.groupBox)
        self.VE_ContrastAgentLineEdit.setEnabled(False)
        self.VE_ContrastAgentLineEdit.setMinimumSize(QtCore.QSize(210, 28))
        self.VE_ContrastAgentLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.VE_ContrastAgentLineEdit.setObjectName("VE_ContrastAgentLineEdit")
        self.gridLayout.addWidget(self.VE_ContrastAgentLineEdit, 4, 3, 1, 1)
        self.VE_ContrastAgentLabel = QtWidgets.QLabel(parent=self.groupBox)
        self.VE_ContrastAgentLabel.setMinimumSize(QtCore.QSize(110, 0))
        self.VE_ContrastAgentLabel.setMaximumSize(QtCore.QSize(110, 16777215))
        self.VE_ContrastAgentLabel.setObjectName("VE_ContrastAgentLabel")
        self.gridLayout.addWidget(self.VE_ContrastAgentLabel, 4, 1, 1, 1)
        self.VE_FilePathLabel = QtWidgets.QLabel(parent=self.groupBox)
        self.VE_FilePathLabel.setMinimumSize(QtCore.QSize(110, 0))
        self.VE_FilePathLabel.setMaximumSize(QtCore.QSize(110, 16777215))
        self.VE_FilePathLabel.setWordWrap(True)
        self.VE_FilePathLabel.setObjectName("VE_FilePathLabel")
        self.gridLayout.addWidget(self.VE_FilePathLabel, 7, 1, 1, 1)
        self.VE_ReconstructionLineEdit = QtWidgets.QLineEdit(parent=self.groupBox)
        self.VE_ReconstructionLineEdit.setEnabled(False)
        self.VE_ReconstructionLineEdit.setMinimumSize(QtCore.QSize(210, 28))
        self.VE_ReconstructionLineEdit.setMaximumSize(QtCore.QSize(16777215, 28))
        self.VE_ReconstructionLineEdit.setObjectName("VE_ReconstructionLineEdit")
        self.gridLayout.addWidget(self.VE_ReconstructionLineEdit, 6, 3, 1, 1)
        self.VE_AcquisitionLabel = QtWidgets.QLabel(parent=self.groupBox)
        self.VE_AcquisitionLabel.setMinimumSize(QtCore.QSize(110, 0))
        self.VE_AcquisitionLabel.setMaximumSize(QtCore.QSize(110, 16777215))
        self.VE_AcquisitionLabel.setObjectName("VE_AcquisitionLabel")
        self.gridLayout.addWidget(self.VE_AcquisitionLabel, 5, 1, 1, 1)
        self.VE_SessionComboBox = QtWidgets.QComboBox(parent=self.groupBox)
        self.VE_SessionComboBox.setEnabled(False)
        self.VE_SessionComboBox.setObjectName("VE_SessionComboBox")
        self.gridLayout.addWidget(self.VE_SessionComboBox, 2, 3, 1, 1)
        self.VE_ModalityComboBox = QtWidgets.QComboBox(parent=self.groupBox)
        self.VE_ModalityComboBox.setEnabled(False)
        self.VE_ModalityComboBox.setObjectName("VE_ModalityComboBox")
        self.VE_ModalityComboBox.addItem("")
        self.VE_ModalityComboBox.addItem("")
        self.VE_ModalityComboBox.addItem("")
        self.VE_ModalityComboBox.addItem("")
        self.VE_ModalityComboBox.addItem("")
        self.VE_ModalityComboBox.addItem("")
        self.VE_ModalityComboBox.addItem("")
        self.gridLayout.addWidget(self.VE_ModalityComboBox, 1, 3, 1, 1)
        self.VE_ModalityLabel = QtWidgets.QLabel(parent=self.groupBox)
        self.VE_ModalityLabel.setObjectName("VE_ModalityLabel")
        self.gridLayout.addWidget(self.VE_ModalityLabel, 1, 1, 1, 1)
        self.verticalLayout_2.addWidget(self.groupBox)
        self.progressBar = QtWidgets.QProgressBar(parent=self.ImportTab)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName("progressBar")
        self.verticalLayout_2.addWidget(self.progressBar)
        self.StartImportLayout = QtWidgets.QHBoxLayout()
        self.StartImportLayout.setObjectName("StartImportLayout")
        spacerItem6 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.StartImportLayout.addItem(spacerItem6)
        self.StartImportPushButton = QtWidgets.QPushButton(parent=self.ImportTab)
        self.StartImportPushButton.setObjectName("StartImportPushButton")
        self.StartImportLayout.addWidget(self.StartImportPushButton)
        spacerItem7 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.StartImportLayout.addItem(spacerItem7)
        self.verticalLayout_2.addLayout(self.StartImportLayout)
        self.tabWidget.addTab(self.ImportTab, "")
        self.gridLayout_4.addWidget(self.splitter, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1105, 21))
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
        self.AR_BrowsePushButton.setText(_translate("MainWindow", "Browse File"))
        self.AR_IsDicomFolderCheckBox.setText(_translate("MainWindow", "Is DICOM Folder ?"))
        self.AR_ModalityLabel.setText(_translate("MainWindow", "Modality"))
        self.AR_ModalityComboBox.setItemText(0, _translate("MainWindow", "T1w (anat)"))
        self.AR_ModalityComboBox.setItemText(1, _translate("MainWindow", "T2w (anat)"))
        self.AR_ModalityComboBox.setItemText(2, _translate("MainWindow", "T1rho (anat)"))
        self.AR_ModalityComboBox.setItemText(3, _translate("MainWindow", "T2start (anat)"))
        self.AR_ModalityComboBox.setItemText(4, _translate("MainWindow", "FLAIR (anat)"))
        self.AR_ModalityComboBox.setItemText(5, _translate("MainWindow", "ct (anat)"))
        self.AR_ModalityComboBox.setItemText(6, _translate("MainWindow", "ieeg (ieeg)"))
        self.AR_ModalityComboBox.setItemText(7, _translate("MainWindow", "photo (ieeg)"))
        self.AR_SessionLabel.setText(_translate("MainWindow", "Session"))
        self.AR_TaskLabel.setText(_translate("MainWindow", "Task"))
        self.AR_ContrastAgentLabel.setText(_translate("MainWindow", "Contrast Agent"))
        self.AR_AcquisitionLabel.setText(_translate("MainWindow", "Acquisition"))
        self.AR_ReconstructionLabel.setText(_translate("MainWindow", "Reconstruction"))
        self.AR_AddPushButton.setText(_translate("MainWindow", "Add"))
        self.AR_RemovePushButton.setText(_translate("MainWindow", "Remove"))
        self.groupBox.setTitle(_translate("MainWindow", "View / Edit Files"))
        self.VE_SessionLabel.setText(_translate("MainWindow", "Session :"))
        self.VE_EditPushButton.setText(_translate("MainWindow", "Edit"))
        self.VE_CancelPushButton.setText(_translate("MainWindow", "Cancel"))
        self.VE_TaskLabel.setText(_translate("MainWindow", "Task :"))
        self.VE_ReconstructionLabel.setText(_translate("MainWindow", "Reconstruction :"))
        self.VE_ContrastAgentLabel.setText(_translate("MainWindow", "Contrast Agent :"))
        self.VE_FilePathLabel.setText(_translate("MainWindow", "Path :"))
        self.VE_AcquisitionLabel.setText(_translate("MainWindow", "Acquisition :"))
        self.VE_ModalityComboBox.setItemText(0, _translate("MainWindow", "T1w (anat)"))
        self.VE_ModalityComboBox.setItemText(1, _translate("MainWindow", "T2w (anat)"))
        self.VE_ModalityComboBox.setItemText(2, _translate("MainWindow", "T1rho (anat)"))
        self.VE_ModalityComboBox.setItemText(3, _translate("MainWindow", "T2start (anat)"))
        self.VE_ModalityComboBox.setItemText(4, _translate("MainWindow", "FLAIR (anat)"))
        self.VE_ModalityComboBox.setItemText(5, _translate("MainWindow", "ieeg (ieeg)"))
        self.VE_ModalityComboBox.setItemText(6, _translate("MainWindow", "photo (ieeg)"))
        self.VE_ModalityLabel.setText(_translate("MainWindow", "Modality :"))
        self.StartImportPushButton.setText(_translate("MainWindow", "Start Import"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.ImportTab), _translate("MainWindow", "Import Files"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.actionLoad_Bids_Dataset_Folder.setText(_translate("MainWindow", "Load Bids Dataset Folder"))
        self.actionOpen_Bids_Dataset.setText(_translate("MainWindow", "Open Bids Dataset"))
        self.actionOpen_Multiple_Bids_Datasets.setText(_translate("MainWindow", "Open Multiple Bids Datasets"))
        self.actionNew_Bids_Dataset.setText(_translate("MainWindow", "New Bids Dataset"))
        self.actionClose.setText(_translate("MainWindow", "Close"))
from ui.PatientTableWidget import PatientTableWidget
