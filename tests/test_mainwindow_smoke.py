"""GUI smoke test: the main window constructs offscreen with all tabs wired.

This is the cheap-but-high-value test the plan calls for — it exercises the full
``MainWindow.__init__`` (setupUi, controller creation, every ``.connect(...)``
slot lookup, and the runtime ``insertTab`` of all three split-out tab QWidgets)
without a visible window. It catches import errors, broken signal wiring, and the
tab-index hazard of the runtime-assembled tab widget.

Runs under ``QT_QPA_PLATFORM=offscreen`` (set in CI and below).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.ui.MainWindow import MainWindow
from bidsificator.ui.tabs.import_files_tab import ImportFilesTab
from bidsificator.ui.tabs.import_subjects_tab import ImportSubjectsTab
from bidsificator.ui.tabs.participants_tab import ParticipantsTab


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qapp):
    win = MainWindow()
    yield win
    win.close()
    win.deleteLater()


def test_mainwindow_constructs(window):
    """The window instantiates and wires its controller without raising."""
    assert window is not None
    assert window._main_controller is not None
    # All three tabs are self-contained QWidgets built at runtime.
    assert isinstance(window._participants_tab, ParticipantsTab)
    assert isinstance(window._import_files_tab, ImportFilesTab)
    assert isinstance(window._import_subjects_tab, ImportSubjectsTab)
    assert window._import_subjects_tab._file_editor is not None


def test_all_tab_widgets_exist(window):
    """Each tab's key widgets exist on their own QWidget."""
    # Participants tab (own QWidget); the file tree is host chrome.
    assert window.fileTreeView is not None
    assert window._participants_tab.CreateSubjectPushButton is not None
    assert window._participants_tab.tableWidget is not None
    # Import Files tab (own QWidget)
    assert window._import_files_tab.ModalityComboBox is not None
    assert window._import_files_tab.ImportFileListWidget is not None
    assert window._import_files_tab.SessionComboBox is not None
    # Import Subjects tab (own QWidget)
    assert window._import_subjects_tab.IS_SubjectListWidget is not None
    assert window._import_subjects_tab.lineEdit is not None


def test_tab_widget_order_and_titles(window):
    """The tab widget has exactly the three tabs, in order, each being the
    split-out QWidget at its runtime index (guards the insertTab hazard)."""
    tabs = window.tabWidget
    assert tabs.count() == 3
    assert tabs.tabText(0) == "Participants"
    assert tabs.tabText(1) == "Import Files"
    assert tabs.tabText(2) == "Import Subjects"
    assert tabs.widget(0) is window._participants_tab
    assert tabs.widget(1) is window._import_files_tab
    assert tabs.widget(2) is window._import_subjects_tab


def test_modality_dropdown_is_populated(window):
    """populate_modality_dropdown ran during the tab's __init__ and filled it."""
    assert window._import_files_tab.ModalityComboBox.count() > 0


def test_tab_slots_resolve(window):
    """Each split-out tab's key slot resolves on its own widget."""
    assert callable(window._participants_tab.create_subject)
    assert callable(window._import_files_tab.add_multiple_files)
    assert callable(window._import_subjects_tab.parse_subject_to_import)


def test_host_owns_file_tree_chrome(window):
    """The file-tree browser + validator ops stay on the host, not a tab."""
    assert callable(window.show_file_tree_context_menu)
    assert callable(window.validate_bids_dataset)
    # The tree rename/delete ops reach the subject controller via the tab.
    assert hasattr(window._participants_tab, "subject_controller")
