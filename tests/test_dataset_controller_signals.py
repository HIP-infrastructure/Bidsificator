"""Tests for the DatasetController signal contract introduced in PR 8b.

The controller is now UI-free: instead of showing QMessageBox / the validation
dialogs itself, it emits ``operation_failed(title, message)``,
``validation_started(msg)``, and ``validation_finished(result)`` for the view to
render. These tests pin that contract without a GUI, and confirm the input-
gathering (folder/name) moved to the view — the controller takes those values as
arguments rather than opening dialogs.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.controllers.DatasetController import DatasetController


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _capture(signal):
    """Collect a signal's emitted argument tuples into a list."""
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


def test_create_new_dataset_empty_name_emits_operation_failed(qapp):
    ctrl = DatasetController()
    failures = _capture(ctrl.operation_failed)

    ok, _msg = ctrl.create_new_dataset("/some/folder", "   ")
    assert ok is False
    assert len(failures) == 1
    assert failures[0][0] == "Dataset Name empty"


def test_create_new_dataset_no_folder_is_silent(qapp):
    ctrl = DatasetController()
    failures = _capture(ctrl.operation_failed)

    ok, msg = ctrl.create_new_dataset("", "name")
    assert ok is False
    assert msg == "No folder selected"
    assert failures == []  # a cancelled folder selection shows no dialog


def test_load_existing_dataset_failure_emits_operation_failed(qapp, tmp_path):
    ctrl = DatasetController()
    failures = _capture(ctrl.operation_failed)

    missing = tmp_path / "not_there"
    ok, _msg = ctrl.load_existing_dataset(str(missing))
    assert ok is False
    assert len(failures) == 1
    assert failures[0][0] == "Dataset Loading Failed"


def test_create_subject_without_dataset_emits_operation_failed(qapp):
    ctrl = DatasetController()
    failures = _capture(ctrl.operation_failed)

    ok, _err = ctrl.create_subject("sub-01")
    assert ok is False
    assert len(failures) == 1
    assert failures[0][0] == "No dataset selected"


def test_validate_without_loaded_dataset_emits_failure_not_validation(qapp):
    ctrl = DatasetController()
    started = _capture(ctrl.validation_started)
    finished = _capture(ctrl.validation_finished)
    failures = _capture(ctrl.operation_failed)

    ok, _msg = ctrl.validate_dataset()
    assert ok is False
    assert started == []   # never announced a start
    assert finished == []
    assert len(failures) == 1
    assert failures[0][0] == "No Dataset found"


def test_validate_loaded_dataset_emits_start_then_finish(qapp, tmp_path):
    ctrl = DatasetController()
    # Create a real minimal BIDS dataset so validation has something to run on.
    ok, path = ctrl.create_new_dataset(str(tmp_path), "demo")
    assert ok, path

    started = _capture(ctrl.validation_started)
    finished = _capture(ctrl.validation_finished)
    failures = _capture(ctrl.operation_failed)

    ctrl.validate_dataset()

    assert started == [("Validating entire dataset...",)]
    assert len(finished) == 1
    # validation_finished carries the ValidationResult object for the dialog.
    result = finished[0][0]
    assert hasattr(result, "is_valid")
    assert failures == []
