"""Tests for the UI-free ``PatientTableController`` contract (controller-dialog sweep 2/4).

The controller no longer opens ``QInputDialog``/``QMessageBox`` itself: the view
(``PatientTableWidget``) gathers the new-key name and the remove-key confirmation,
and validation/guard failures come back via ``operation_failed(title, message)``.
These tests pin that contract on a real (temp) BIDS dataset bootstrapped through
``DatasetController`` — the same known-good path the dataset-controller tests use.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.controllers.DatasetController import DatasetController
from bidsificator.controllers.PatientTableController import PatientTableController


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


@pytest.fixture
def controller(qapp, tmp_path):
    """A PatientTableController with a loaded dataset holding two subjects."""
    ds = DatasetController()
    ok, path = ds.create_new_dataset(str(tmp_path), "demo")
    assert ok, path

    ptc = PatientTableController(lambda: path)
    assert ptc.load_subjects(path) is True
    # Default keys for a fresh subject are age/sex (see create_subject).
    assert ptc.create_subject("01")[0] is True
    assert ptc.create_subject("02")[0] is True
    return ptc


# --------------------------------------------------------------------------- #
# add_key_after / add_key_before
# --------------------------------------------------------------------------- #

def test_add_key_empty_name_is_silent(controller):
    failures = _capture(controller.operation_failed)
    updates = _capture(controller.keys_updated)

    assert controller.add_key_after(1, "   ") is False
    assert failures == []  # cancelled/empty input shows no message
    assert updates == []


def test_add_duplicate_key_emits_failure(controller):
    failures = _capture(controller.operation_failed)

    assert controller.add_key_after(1, "age") is False  # age already exists
    assert len(failures) == 1
    assert failures[0][0] == "Duplicate Key"


def test_add_new_key_succeeds_and_emits_update(controller):
    updates = _capture(controller.keys_updated)
    failures = _capture(controller.operation_failed)

    assert controller.add_key_after(1, "handedness") is True
    assert failures == []
    assert len(updates) >= 1  # keys_updated fires (via the internal sync + explicitly)
    assert "handedness" in controller.get_subjects_keys_from_data()


def test_add_key_before_delegates(controller):
    assert controller.add_key_before(1, "weight") is True
    assert "weight" in controller.get_subjects_keys_from_data()


# --------------------------------------------------------------------------- #
# remove_key
# --------------------------------------------------------------------------- #

def test_remove_subject_id_column_is_guarded(controller):
    failures = _capture(controller.operation_failed)

    assert controller.remove_key("subject_id") is False
    assert len(failures) == 1
    assert failures[0][0] == "Cannot Remove"


def test_remove_real_key_succeeds(controller):
    # The confirmation lives in the view now, so calling remove_key removes it.
    updates = _capture(controller.keys_updated)

    assert controller.remove_key("age") is True
    assert len(updates) >= 1
    assert "age" not in controller.get_subjects_keys_from_data()


# --------------------------------------------------------------------------- #
# update_subject_field
# --------------------------------------------------------------------------- #

def test_update_invalid_subject_id_emits_failure(controller):
    failures = _capture(controller.operation_failed)

    assert controller.update_subject_field("01", "subject_id", "bad name!") is False
    assert len(failures) == 1
    assert failures[0][0] == "Invalid Subject ID"


def test_update_duplicate_subject_id_emits_failure(controller):
    failures = _capture(controller.operation_failed)

    # Renaming subject 01 to the existing 02 is a duplicate.
    assert controller.update_subject_field("01", "subject_id", "02") is False
    assert len(failures) == 1
    assert failures[0][0] == "Duplicate Subject ID"


def test_update_optional_field_succeeds(controller):
    updated = _capture(controller.subject_updated)
    failures = _capture(controller.operation_failed)

    assert controller.update_subject_field("01", "age", "30") is True
    assert failures == []
    assert updated == [("01",)]
