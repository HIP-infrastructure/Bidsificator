"""Tests for the UI-free ``FileEditorController.add_custom_task`` contract.

Part of the controller-dialog sweep: the "Other" task option used to open a
``QInputDialog`` and show ``QMessageBox`` warnings from inside the controller.
The controller is now UI-free — the view gathers the task-name text and this
method validates it, emitting ``operation_failed(title, message)`` for the view
to render instead of showing dialogs itself. These tests pin that contract
without a GUI (same dependency-free pattern as ``test_dataset_controller_signals``).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.controllers.FileEditorController import FileEditorController


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


def test_empty_task_name_emits_failure(qapp):
    ctrl = FileEditorController()
    failures = _capture(ctrl.operation_failed)
    updates = _capture(ctrl.task_list_updated)

    final, tasks = ctrl.add_custom_task("   ", ["rest", "Other"])

    assert final == ""
    assert tasks == ["rest", "Other"]  # unchanged
    assert len(failures) == 1
    assert failures[0][0] == "Task Name empty"
    assert updates == []  # nothing added, no list update


def test_invalid_task_name_emits_failure(qapp):
    ctrl = FileEditorController()
    failures = _capture(ctrl.operation_failed)

    # Hyphens are not valid in a BIDS entity label, so validation rejects this.
    final, tasks = ctrl.add_custom_task("bad-task", ["rest", "Other"])

    assert final == ""
    assert tasks == ["rest", "Other"]
    assert len(failures) == 1
    assert failures[0][0] == "Invalid Task Name"


def test_valid_task_inserts_before_other_and_emits_update(qapp):
    ctrl = FileEditorController()
    failures = _capture(ctrl.operation_failed)
    updates = _capture(ctrl.task_list_updated)

    final, tasks = ctrl.add_custom_task("memory", ["rest", "Other"])

    assert final == "memory"
    assert tasks == ["rest", "memory", "Other"]  # inserted before "Other"
    assert failures == []
    assert updates == [(["rest", "memory", "Other"],)]


def test_valid_task_appended_when_no_other_entry(qapp):
    ctrl = FileEditorController()
    final, tasks = ctrl.add_custom_task("memory", ["rest"])

    assert final == "memory"
    assert tasks == ["rest", "memory"]  # appended when there is no "Other"
