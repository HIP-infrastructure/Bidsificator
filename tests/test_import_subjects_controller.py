"""Tests for the UI-free ``ImportSubjectsController`` contract (controller-dialog sweep 4/4).

The batch-subject-import controller no longer opens ``QMessageBox``/``QFileDialog``
itself. Warnings arrive via ``operation_failed(title, message)``, informational
messages via ``operation_info(title, message)``; the save-template file dialog and
the 3-button conflict dialog moved to the view (the latter is injected into
``start_batch_import`` as a ``conflict_resolver`` callback). These tests pin the
observable contract without a GUI.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.controllers.FileEditorController import FileEditorController
from bidsificator.controllers.ImportSubjectsController import ImportSubjectsController
from bidsificator.core.BidsFolder import BidsFolder
from bidsificator.models.SubjectDataModel import SubjectData
from bidsificator.workers.BidsSubjectsProcess import check_subject_conflicts
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


def test_on_import_finished_partial_withholds_dialog_dismissed(qapp):
    ctrl = _controller("/data")
    dismissed = _capture(ctrl.dialog_dismissed)
    summary = ImportSummary(
        items=[
            ImportItemOutcome("f.trc", "x", IMPORTED),
            ImportItemOutcome("g.trc", "x", SKIPPED, "missing"),
        ],
        subjects_created=1,
    )

    ctrl._on_import_finished(summary)

    # Partial batch import keeps the amber status visible, so no dialog_dismissed.
    assert dismissed == []


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


# --------------------------------------------------------------------------- #
# conflict pre-check (REQ-GUI-026)                                            #
# --------------------------------------------------------------------------- #

def _dataset_with_subjects(path, *subject_ids):
    """A real BIDS dataset on disk whose participants.tsv lists ``subject_ids``."""
    bids_folder = BidsFolder(str(path))
    for subject_id in subject_ids:
        bids_folder.add_bids_subject(subject_id, {"age": 30, "sex": "F"})
    bids_folder.generate_participants_tsv()
    return path


class _RecordingWorker:
    """Stands in for ImportBidsSubjectsWorker so no import subprocess starts."""

    started = []

    def __init__(self, dataset_path, subjects_data, overwrite_existing, task):
        self.subjects_data = subjects_data
        self.overwrite_existing = overwrite_existing
        self.update_progressbar_signal = self.import_finished = self.error = self

    def connect(self, _slot):
        pass

    def start(self):
        _RecordingWorker.started.append(self)

    def isRunning(self):
        return False


def _controller_with_queued_subjects(monkeypatch, dataset_path, source_file, *subject_ids):
    _RecordingWorker.started = []
    controller_module = sys.modules[ImportSubjectsController.__module__]
    monkeypatch.setattr(controller_module, "ImportBidsSubjectsWorker", _RecordingWorker)
    ctrl = _controller(str(dataset_path))
    for subject_id in subject_ids:
        ctrl._model.add_subject(SubjectData(
            subject_id, files=[{"file_path": str(source_file), "modality": "ieeg"}],
        ))
    return ctrl


def test_check_subject_conflicts_finds_existing_subjects(tmp_path):
    # Regression: the check built "sub-01" but compared it with the bare ids
    # BidsFolder stores ("01"), so it always returned [] and the conflict
    # dialog never appeared.
    dataset = _dataset_with_subjects(tmp_path / "ds", "01")
    queued = [{"subject_id": "01", "files": []}, {"subject_id": "02", "files": []}]

    # Returned with the "sub-" prefix: the controller's skip filter and the
    # dialog both use that form.
    assert check_subject_conflicts(str(dataset), queued) == ["sub-01"]


def test_start_import_into_existing_subject_asks_conflict_resolver(qapp, tmp_path, monkeypatch):
    dataset = _dataset_with_subjects(tmp_path / "ds", "01")
    source = tmp_path / "rec.edf"
    source.write_bytes(b"")
    ctrl = _controller_with_queued_subjects(monkeypatch, dataset, source, "01", "02")
    asked = []

    def cancel(existing):
        asked.append(existing)
        return "cancel"

    assert ctrl.start_batch_import("rest", conflict_resolver=cancel) is False
    assert asked == [["sub-01"]]
    assert _RecordingWorker.started == []


def test_start_import_skip_filters_existing_subject_out(qapp, tmp_path, monkeypatch):
    dataset = _dataset_with_subjects(tmp_path / "ds", "01")
    source = tmp_path / "rec.edf"
    source.write_bytes(b"")
    ctrl = _controller_with_queued_subjects(monkeypatch, dataset, source, "01", "02")

    assert ctrl.start_batch_import("rest", conflict_resolver=lambda _existing: "skip") is True
    (worker,) = _RecordingWorker.started
    assert [s["subject_id"] for s in worker.subjects_data] == ["02"]
    assert worker.overwrite_existing is False
    assert ctrl._skipped_existing == ["sub-01"]
