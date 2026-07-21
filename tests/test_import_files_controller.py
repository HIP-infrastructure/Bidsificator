"""Signal-contract and dialog-free logic tests for :class:`ImportFilesController`.

Follows the dependency-free house pattern (a module-scoped ``QApplication`` and a
small signal-capture helper, as in ``test_dataset_controller_signals.py``) rather
than pulling in pytest-qt: the controller is a plain ``QObject`` and its signals
are observable directly. Only paths that do not open a Qt dialog are exercised.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.controllers.ImportFilesController import ImportFilesController


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


def _controller(dataset_path=""):
    """A controller with a stub dataset-path provider and no parent widget."""
    return ImportFilesController(lambda: dataset_path)


def test_initial_state(qapp):
    ctrl = _controller()
    assert ctrl.file_count == 0
    assert ctrl.current_subject == ""
    assert ctrl.selected_file_index == -1


def test_setting_selected_index_emits_selection_changed(qapp):
    ctrl = _controller()
    seen = _capture(ctrl.selection_changed)

    ctrl.selected_file_index = 3

    # The setter emits the requested index; the model clamps to -1 while the
    # file list is empty, so the stored value stays -1.
    assert seen == [(3,)]
    assert ctrl.selected_file_index == -1


def test_change_subject_without_files_updates_silently(qapp):
    ctrl = _controller()
    # Empty list + ask_user irrelevant: no dialog, just a model update.
    assert ctrl.change_subject("sub-01", ask_user=False) is True
    assert ctrl.current_subject == "sub-01"


def test_contact_labeling_file_roundtrips(qapp):
    ctrl = _controller()
    assert ctrl.contact_labeling_file is None
    ctrl.contact_labeling_file = "/data/labels.xlsx"
    assert ctrl.contact_labeling_file == "/data/labels.xlsx"


def test_check_electrodes_false_when_subject_absent(qapp, tmp_path):
    ctrl = _controller(str(tmp_path))
    assert ctrl._check_electrodes_will_be_overwritten(str(tmp_path), "01") is False


def test_check_electrodes_true_when_file_present(qapp, tmp_path):
    ctrl = _controller(str(tmp_path))
    ieeg_dir = tmp_path / "sub-01" / "ses-01" / "ieeg"
    ieeg_dir.mkdir(parents=True)
    (ieeg_dir / "sub-01_ses-01_electrodes.tsv").write_text("name\n", encoding="utf-8")

    assert ctrl._check_electrodes_will_be_overwritten(str(tmp_path), "01") is True
