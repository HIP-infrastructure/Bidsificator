"""Tests for the UI-free ``ImportSubjectsController`` contract (controller-dialog sweep 4/4).

The batch-subject-import controller no longer opens ``QMessageBox``/``QFileDialog``
itself. Warnings arrive via ``operation_failed(title, message)``, informational
messages via ``operation_info(title, message)``; the save-template file dialog and
the 3-button conflict dialog moved to the view (the latter is injected into
``start_batch_import`` as a ``conflict_resolver`` callback). These tests pin the
observable contract without a GUI.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.controllers.FileEditorController import FileEditorController
from bidsificator.controllers.ImportSubjectsController import ImportSubjectsController
from bidsificator.workers.import_processor import (
    IMPORTED,
    SKIPPED,
    ImportItemOutcome,
    ImportSummary,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


def _controller(dataset_path=""):
    return ImportSubjectsController(lambda: dataset_path, FileEditorController())


# --------------------------------------------------------------------------- #
# terminal outcome handling (UR-GUI-009 ticket 2)                             #
# --------------------------------------------------------------------------- #

def test_on_import_finished_reports_summary_counts(qapp):
    ctrl = _controller("/data")
    completed = _capture(ctrl.import_completed)
    dismissed = _capture(ctrl.dialog_dismissed)
    summary = ImportSummary(
        items=[
            ImportItemOutcome("f.trc", "x", IMPORTED),
            ImportItemOutcome("g.trc", "x", IMPORTED),
        ],
        subjects_created=2,
    )

    ctrl._on_import_finished(summary)

    results = completed[0][0]
    assert results["subjects_imported"] == 2
    assert results["total_files"] == 2  # files actually placed, from the summary
    assert len(dismissed) == 1


def test_on_import_finished_merges_conflict_skips_into_summary(qapp):
    ctrl = _controller("/data")
    completed = _capture(ctrl.import_completed)
    # Two subjects the user skipped at the conflict dialog were filtered out
    # before the worker, so they never reached the subprocess summary.
    ctrl._skipped_existing = ["sub-alice", "sub-bob"]
    summary = ImportSummary(
        items=[ImportItemOutcome("f.trc", "carol", IMPORTED)],
        subjects_created=1,
    )

    ctrl._on_import_finished(summary)

    results = completed[0][0]
    assert results["subjects_imported"] == 1
    assert results["total_files"] == 1
    # The user-skipped subjects are merged back in as skipped items (REQ-GUI-073).
    assert results["summary"]["skipped"] == 2
    skipped_subjects = {
        item["subject"] for item in results["summary"]["items"] if item["status"] == SKIPPED
    }
    assert skipped_subjects == {"sub-alice", "sub-bob"}


# --------------------------------------------------------------------------- #
# start_batch_import pre-checks -> operation_failed
# --------------------------------------------------------------------------- #

def test_start_import_without_dataset_emits_operation_failed(qapp):
    ctrl = _controller(dataset_path="")
    failures = _capture(ctrl.operation_failed)

    assert ctrl.start_batch_import("rest") is False
    assert len(failures) == 1
    assert failures[0][0] == "No Dataset"


def test_start_import_without_subjects_emits_operation_failed(qapp, tmp_path):
    ctrl = _controller(dataset_path=str(tmp_path))  # dataset present, nothing parsed
    failures = _capture(ctrl.operation_failed)

    assert ctrl.start_batch_import("rest") is False
    assert len(failures) == 1
    assert failures[0][0] == "No Subjects"


# --------------------------------------------------------------------------- #
# remove_selected_subjects (confirmation now lives in the view)
# --------------------------------------------------------------------------- #

def test_remove_no_indices_is_noop(qapp):
    ctrl = _controller()
    assert ctrl.remove_selected_subjects([]) is False


# --------------------------------------------------------------------------- #
# set_lookup_table -> operation_failed / operation_info / lookup_table_updated
# --------------------------------------------------------------------------- #

def test_set_lookup_table_clear(qapp):
    ctrl = _controller()
    status = _capture(ctrl.lookup_table_updated)

    assert ctrl.set_lookup_table("") is True
    assert status == [("Lookup table cleared",)]


def test_set_lookup_table_invalid_emits_operation_failed(qapp, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("nope;no;headers\n", encoding="utf-8")  # missing required headers
    ctrl = _controller()
    failures = _capture(ctrl.operation_failed)

    assert ctrl.set_lookup_table(str(bad)) is False
    assert len(failures) == 1
    assert failures[0][0] == "Invalid Lookup Table"


def test_set_lookup_table_valid_emits_operation_info(qapp, tmp_path):
    good = tmp_path / "lut.csv"
    good.write_text("FolderID;CenterID;SubjectID\nPat_1;1;1\n", encoding="utf-8")
    ctrl = _controller()
    infos = _capture(ctrl.operation_info)
    failures = _capture(ctrl.operation_failed)

    assert ctrl.set_lookup_table(str(good)) is True
    assert failures == []
    assert len(infos) == 1
    assert infos[0][0] == "Lookup Table Loaded"


# --------------------------------------------------------------------------- #
# save_lookup_template (file dialog now lives in the view)
# --------------------------------------------------------------------------- #

def test_save_lookup_template_creates_file(qapp, tmp_path):
    ctrl = _controller()
    target = str(tmp_path / "tmpl.csv")

    ok, message = ctrl.save_lookup_template(target)
    assert ok is True
    assert "Template created" in message
    assert Path(target).exists()


def test_save_lookup_template_appends_csv_extension(qapp, tmp_path):
    ctrl = _controller()

    ok, _message = ctrl.save_lookup_template(str(tmp_path / "noext"))
    assert ok is True
    assert (tmp_path / "noext.csv").exists()
