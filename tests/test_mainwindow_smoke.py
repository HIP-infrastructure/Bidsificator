"""GUI smoke test: the main window constructs offscreen with all tabs wired.

This is the cheap-but-high-value test the plan calls for — it exercises the full
``MainWindow.__init__`` (setupUi, controller creation, every ``.connect(...)``
slot lookup, and the runtime ``insertTab`` of the split-out ``ImportFilesTab``
and ``ImportSubjectsTab`` QWidgets) without a visible window. It catches import
errors, broken signal wiring, MRO regressions in the remaining Participants
mixin, and the tab-index hazard of the half-migrated ``.ui`` split.

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
    # The Import Files and Import Subjects tabs are self-contained QWidgets.
    assert isinstance(window._import_files_tab, ImportFilesTab)
    assert isinstance(window._import_subjects_tab, ImportSubjectsTab)
    assert window._import_subjects_tab._file_editor is not None


def test_all_tab_widgets_exist(window):
    """Each tab's key widgets exist (on the window, or on the split-out tabs)."""
    # Participants tab (still inline mixin)
    assert window.fileTreeView is not None
    assert window.CreateSubjectPushButton is not None
    # Import Files tab (own QWidget)
    assert window._import_files_tab.ModalityComboBox is not None
    assert window._import_files_tab.ImportFileListWidget is not None
    assert window._import_files_tab.SessionComboBox is not None
    # Import Subjects tab (own QWidget)
    assert window._import_subjects_tab.IS_SubjectListWidget is not None
    assert window._import_subjects_tab.lineEdit is not None


def test_tab_widget_order_and_titles(window):
    """The tab widget has exactly the three tabs, in order, with the split-out
    QWidgets installed at their runtime indices (guards the insertTab hazard)."""
    tabs = window.tabWidget
    assert tabs.count() == 3
    assert tabs.tabText(0) == "Participants"
    assert tabs.tabText(1) == "Import Files"
    assert tabs.tabText(2) == "Import Subjects"
    assert tabs.widget(1) is window._import_files_tab
    assert tabs.widget(2) is window._import_subjects_tab


def test_modality_dropdown_is_populated(window):
    """populate_modality_dropdown ran during the tab's __init__ and filled it."""
    assert window._import_files_tab.ModalityComboBox.count() > 0


def test_tab_slots_resolve(window):
    """The Participants slot resolves on the window; the split-out tabs' slots on them."""
    assert callable(window.create_subject)
    assert callable(window._import_files_tab.add_multiple_files)
    assert callable(window._import_subjects_tab.parse_subject_to_import)
