"""Participants tab — a self-contained ``QWidget`` (9d.3).

Owns subject creation and the subject table (``PatientTableWidget``). Built from
``forms/ParticipantsTab.ui``. The ``MainController`` is injected by the host.

The file-tree view and its context-menu operations (validate / rename / delete)
are NOT here: that tree lives in the left splitter pane (window chrome, outside
the tab widget), so those handlers stay on ``MainWindow``. When a tree operation
needs the subject controller it reaches it through this tab's ``subject_controller``
accessor; the tab owns the ``PatientTableWidget`` and thus its controller.

Cross-tab: the tab re-emits ``subject_updated`` (from its table) so the host can
refresh the dataset subjects and the Import Files subject dropdown.
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QWidget

from ...forms.ParticipantsTab_ui import Ui_ParticipantsTab

if TYPE_CHECKING:
    from ...controllers.MainController import MainController

logger = logging.getLogger(__name__)


class ParticipantsTab(QWidget, Ui_ParticipantsTab):
    """Participants tab: subject creation + the subject table."""

    # Re-emitted from the PatientTableWidget so the host can react cross-tab.
    subject_updated = pyqtSignal()

    def __init__(self, main_controller: "MainController", parent: QWidget | None = None):
        super().__init__(parent)
        self.setupUi(self)

        self._main_controller = main_controller

        # The PatientTableWidget owns its own PatientTableController; give it the
        # dataset-path provider (reads the live dataset path from the controller).
        self.tableWidget.initialize_controller(self._get_dataset_path)
        # Re-emit the table's subject_updated as this tab's own signal.
        self.tableWidget.subject_updated.connect(self.subject_updated)

        self.CreateSubjectPushButton.clicked.connect(self.create_subject)
        self.SubjectLineEdit.setCursorPosition(len(self.SubjectLineEdit.text()))

    # --------------------------------------------------------------------- #
    # accessors for the host (file-tree chrome reaches the table controller here)
    # --------------------------------------------------------------------- #

    def _get_dataset_path(self) -> str:
        """Dataset path provider for the PatientTableWidget controller."""
        return self._main_controller.dataset_controller.dataset_path

    @property
    def subject_controller(self):
        """The PatientTableController (used by the host's tree rename/delete ops)."""
        return self.tableWidget._controller

    def refresh_table(self, dataset_path: str):
        """Reload the subject table for the given dataset path (host calls this)."""
        self.tableWidget.LoadSubjectsInTableWidget(dataset_path)

    # --------------------------------------------------------------------- #
    # subject creation
    # --------------------------------------------------------------------- #

    def create_subject(self):
        """Create a new subject using the controller."""
        subject_name = self.SubjectLineEdit.text().strip()

        if not subject_name:
            return  # Don't create empty subjects

        # Strip "sub-" prefix if user included it (case-insensitive)
        if subject_name.lower().startswith("sub-"):
            subject_name = subject_name[4:]

        # Create subject using PatientTableWidget controller
        if self.tableWidget._controller:
            success, error = self.tableWidget._controller.create_subject(subject_name)
            if success:
                # Clear the input field after successful creation
                self.SubjectLineEdit.clear()
                # Dropdown/table updates are handled by signals
            else:
                QMessageBox.warning(self, "Create Subject Failed", error)
