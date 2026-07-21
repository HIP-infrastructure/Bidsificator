"""GUI smoke test: the main window constructs offscreen with all tabs wired.

This is the cheap-but-high-value test the plan calls for — it exercises the full
``MainWindow.__init__`` (setupUi, the tab setup, controller creation, every
``.connect(...)`` slot lookup, and the runtime ``insertTab`` of the split-out
``ImportSubjectsTab`` QWidget) without a visible window. It catches import
errors, broken signal wiring, MRO regressions in the remaining mixins, and the
tab-index hazard of the half-migrated ``.ui`` split.

Runs under ``QT_QPA_PLATFORM=offscreen`` (set in CI and below).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.ui.MainWindow import MainWindow
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
    # The Import Subjects tab is now a self-contained QWidget owning the FileEditor.
    assert isinstance(window._import_subjects_tab, ImportSubjectsTab)
    assert window._import_subjects_tab._file_editor is not None


def test_all_tab_widgets_exist(window):
    """Each tab's key widgets exist (on the window, or on the split-out tab)."""
    # Participants tab (still inline)
    assert window.fileTreeView is not None
    assert window.CreateSubjectPushButton is not None
    # Import Files tab (still inline)
    assert window.ModalityComboBox is not None
    assert window.ImportFileListWidget is not None
    assert window.SessionComboBox is not None
    # Import Subjects tab (own QWidget)
    assert window._import_subjects_tab.IS_SubjectListWidget is not None
    assert window._import_subjects_tab.lineEdit is not None


def test_tab_widget_order_and_titles(window):
    """The tab widget has exactly the three tabs, in order, with the split-out
    ImportSubjectsTab installed at index 2 (guards the insertTab index hazard)."""
    tabs = window.tabWidget
    assert tabs.count() == 3
    assert tabs.tabText(0) == "Participants"
    assert tabs.tabText(1) == "Import Files"
    assert tabs.tabText(2) == "Import Subjects"
    assert tabs.widget(2) is window._import_subjects_tab


def test_modality_dropdown_is_populated(window):
    """populate_modality_dropdown ran during __init__ and filled the combo box."""
    assert window.ModalityComboBox.count() > 0


def test_tab_slots_resolve(window):
    """Inline-mixin slots resolve on the window; the subjects-tab slot on the tab."""
    for slot in ("create_subject", "add_multiple_files"):
        assert callable(getattr(window, slot))
    assert callable(window._import_subjects_tab.parse_subject_to_import)
