"""GUI smoke test: the main window constructs offscreen with all tabs wired.

This is the cheap-but-high-value test the plan calls for — it exercises the full
``MainWindow.__init__`` (setupUi, the three tab mixins' setup, controller
creation, and every ``.connect(...)`` slot lookup) without a visible window.
It catches import errors, broken signal wiring, and MRO regressions in the
per-tab mixin split — none of which the pure-logic tests would surface.

Runs under ``QT_QPA_PLATFORM=offscreen`` (set in CI and below).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.ui.MainWindow import MainWindow


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
    assert window._import_subject_file_editor is not None


def test_all_tab_widgets_exist(window):
    """Each tab's key widgets were created by setupUi + the mixin setup."""
    # Participants tab
    assert window.fileTreeView is not None
    assert window.CreateSubjectPushButton is not None
    # Import Files tab
    assert window.ModalityComboBox is not None
    assert window.ImportFileListWidget is not None
    assert window.SessionComboBox is not None
    # Import Subjects tab
    assert window.IS_SubjectListWidget is not None
    assert window.lineEdit is not None


def test_modality_dropdown_is_populated(window):
    """populate_modality_dropdown ran during __init__ and filled the combo box."""
    assert window.ModalityComboBox.count() > 0


def test_tab_mixin_methods_resolve_via_mro(window):
    """Slots from each mixin resolve on the live window (the mixin arrangement)."""
    # ParticipantsTabMixin, ImportFilesTabMixin, ImportSubjectsTabMixin
    for slot in ("create_subject", "add_multiple_files", "parse_subject_to_import"):
        assert callable(getattr(window, slot))
