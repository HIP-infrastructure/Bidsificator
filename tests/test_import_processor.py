"""Unit tests for the import worker processors and the pipe-message classifier.

Both ``processBidsFiles`` and ``processBidsSubjects`` are plain functions taking
a ``conn``; these tests drive them with a recording stub connection and a
tmp-path dataset (no multiprocessing). ``BidsSubject.add_file`` is patched at the
class level to control per-file outcomes deterministically without real
neuroimaging conversion. Covers the outcome-tracking requirements of UR-GUI-009
ticket 1 (REQ-GUI-065-070).
"""

import pytest

from bidsificator.core.BidsFolder import BidsFolder
from bidsificator.core.BidsSubjectSchema import BidsSubject
from bidsificator.workers.BidsFilesProcess import processBidsFiles
from bidsificator.workers.BidsSubjectsProcess import processBidsSubjects
from bidsificator.workers.import_processor import (
    FAILED,
    IMPORTED,
    PROGRESS_DONE,
    PROGRESS_ERROR,
    SKIPPED,
    ImportItemOutcome,
    ImportSummary,
    MessageKind,
    classify_message,
)


class RecordingConn:
    """Stand-in for the child end of an ``mp.Pipe`` that records what was sent."""

    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)

    @property
    def summary(self):
        """The terminal message (last thing sent)."""
        return self.sent[-1]

    @property
    def progress_values(self):
        """The int progress values sent before the terminal message."""
        return [m for m in self.sent[:-1] if isinstance(m, int)]


@pytest.fixture(autouse=True)
def _silence_worker_logging(monkeypatch):
    """The processors call setup_logging() (meant for a fresh subprocess); make it
    a no-op so tests don't spawn file handlers or duplicate the root config."""
    monkeypatch.setattr("bidsificator.workers.BidsFilesProcess.setup_logging", lambda: None)
    monkeypatch.setattr("bidsificator.workers.BidsSubjectsProcess.setup_logging", lambda: None)


def _make_source_file(tmp_path, name="data.trc"):
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    path = src / name
    path.write_bytes(b"dummy")
    return str(path)


def _make_dataset_with_subject(tmp_path, subject_id="test01"):
    """Create a dataset on disk with one subject recorded in participants.tsv, so
    a fresh BidsFolder(dataset_path) rediscovers it."""
    dataset = tmp_path / "dataset"
    folder = BidsFolder(str(dataset))
    folder.add_bids_subject(subject_id, {"age": 25, "sex": "M"})
    folder.generate_participants_tsv()
    return str(dataset)


def _stub_add_file_ok(monkeypatch):
    def fake(self, source_path, datatype, entities=None, suffix=None, metadata=None, target_format=None):
        return {"target_path": str(source_path)}
    monkeypatch.setattr(BidsSubject, "add_file", fake)


def _stub_add_file_raises(monkeypatch, message="boom"):
    def fake(self, source_path, datatype, entities=None, suffix=None, metadata=None, target_format=None):
        raise RuntimeError(message)
    monkeypatch.setattr(BidsSubject, "add_file", fake)


# --------------------------------------------------------------------------- #
# classify_message                                                            #
# --------------------------------------------------------------------------- #

class TestClassifyMessage:
    def test_progress_values(self):
        assert classify_message(0) is MessageKind.PROGRESS
        assert classify_message(50) is MessageKind.PROGRESS
        assert classify_message(100) is MessageKind.PROGRESS

    def test_done_sentinel(self):
        assert classify_message(PROGRESS_DONE) is MessageKind.DONE

    def test_error_sentinel(self):
        assert classify_message(PROGRESS_ERROR) is MessageKind.ERROR
        assert classify_message(-5) is MessageKind.ERROR

    def test_summary(self):
        assert classify_message(ImportSummary()) is MessageKind.SUMMARY

    def test_garbage_is_unknown(self):
        # A non-int terminal message must NOT reach an ordering comparison.
        assert classify_message("done") is MessageKind.UNKNOWN
        assert classify_message(None) is MessageKind.UNKNOWN
        assert classify_message(3.14) is MessageKind.UNKNOWN
        assert classify_message({"items": []}) is MessageKind.UNKNOWN
        assert classify_message(200) is MessageKind.UNKNOWN

    def test_bool_is_not_progress(self):
        # bool is an int subclass; guard against True/False being read as progress.
        assert classify_message(True) is MessageKind.UNKNOWN
        assert classify_message(False) is MessageKind.UNKNOWN


class TestImportSummaryCounts:
    def test_counts_derive_from_items(self):
        summary = ImportSummary(items=[
            ImportItemOutcome("a", "s", IMPORTED),
            ImportItemOutcome("b", "s", FAILED, "boom"),
            ImportItemOutcome("c", "s", SKIPPED, "missing"),
            ImportItemOutcome("d", "s", IMPORTED),
        ])
        assert summary.imported == 2
        assert summary.failed == 1
        assert summary.skipped == 1
        assert summary.total == 4


# --------------------------------------------------------------------------- #
# processBidsFiles (single-file import path)                                  #
# --------------------------------------------------------------------------- #

class TestProcessBidsFiles:
    def test_imported_file(self, tmp_path, monkeypatch):
        _stub_add_file_ok(monkeypatch)
        dataset = _make_dataset_with_subject(tmp_path)
        src = _make_source_file(tmp_path)
        conn = RecordingConn()

        processBidsFiles(conn, dataset, "test01",
                         [{"file_path": src, "modality": "ieeg (ieeg)"}])

        summary = conn.summary
        assert isinstance(summary, ImportSummary)
        assert summary.imported == 1
        assert summary.failed == 0
        assert summary.skipped == 0
        assert summary.warnings == []
        assert 100 in conn.progress_values

    def test_missing_file_is_skipped_but_progresses(self, tmp_path, monkeypatch):
        _stub_add_file_ok(monkeypatch)
        dataset = _make_dataset_with_subject(tmp_path)
        conn = RecordingConn()

        processBidsFiles(conn, dataset, "test01",
                         [{"file_path": str(tmp_path / "nope.trc"), "modality": "ieeg (ieeg)"}])

        summary = conn.summary
        assert summary.skipped == 1
        assert summary.imported == 0
        assert "not found" in summary.items[0].reason
        # Progress still reaches 100 despite the skip (REQ-GUI-067).
        assert 100 in conn.progress_values

    def test_unrecognized_modality_is_skipped(self, tmp_path, monkeypatch):
        _stub_add_file_ok(monkeypatch)
        dataset = _make_dataset_with_subject(tmp_path)
        src = _make_source_file(tmp_path)
        conn = RecordingConn()

        # "BOLD (func)" is offered in the UI but unhandled by the resolver.
        processBidsFiles(conn, dataset, "test01",
                         [{"file_path": src, "modality": "BOLD (func)"}])

        summary = conn.summary
        assert summary.skipped == 1
        assert summary.imported == 0
        assert "BOLD (func)" in summary.items[0].reason

    def test_add_file_failure_is_recorded_with_real_reason(self, tmp_path, monkeypatch):
        _stub_add_file_raises(monkeypatch, "conversion exploded")
        dataset = _make_dataset_with_subject(tmp_path)
        src = _make_source_file(tmp_path)
        conn = RecordingConn()

        processBidsFiles(conn, dataset, "test01",
                         [{"file_path": src, "modality": "ieeg (ieeg)"}])

        summary = conn.summary
        assert summary.failed == 1
        assert summary.imported == 0
        assert summary.items[0].status == FAILED
        assert summary.items[0].reason == "conversion exploded"

    def test_progress_reaches_100_with_mixed_outcomes(self, tmp_path, monkeypatch):
        _stub_add_file_ok(monkeypatch)
        dataset = _make_dataset_with_subject(tmp_path)
        good = _make_source_file(tmp_path, "good.trc")
        conn = RecordingConn()

        processBidsFiles(conn, dataset, "test01", [
            {"file_path": str(tmp_path / "missing.trc"), "modality": "ieeg (ieeg)"},
            {"file_path": good, "modality": "ieeg (ieeg)"},
        ])

        summary = conn.summary
        assert summary.total == 2
        assert summary.imported == 1
        assert summary.skipped == 1
        assert max(conn.progress_values) == 100

    def test_subject_not_found_hard_aborts(self, tmp_path, monkeypatch):
        _stub_add_file_ok(monkeypatch)
        dataset = _make_dataset_with_subject(tmp_path)
        src = _make_source_file(tmp_path)
        conn = RecordingConn()

        processBidsFiles(conn, dataset, "ghost",
                         [{"file_path": src, "modality": "ieeg (ieeg)"}])

        # Hard abort: PROGRESS_ERROR sentinel, no summary.
        assert conn.sent == [PROGRESS_ERROR]

    def test_contact_labeling_attach_failure_is_a_warning(self, tmp_path, monkeypatch):
        _stub_add_file_ok(monkeypatch)
        dataset = _make_dataset_with_subject(tmp_path)
        src = _make_source_file(tmp_path)
        conn = RecordingConn()

        # A nonexistent labeling file makes set_contact_labeling_file raise.
        processBidsFiles(conn, dataset, "test01",
                         [{"file_path": src, "modality": "ieeg (ieeg)"}],
                         contact_labeling_file="/nonexistent/labels.xlsx")

        summary = conn.summary
        # The attach failure is summary-level, not a per-item failure.
        assert len(summary.warnings) == 1
        assert "labels.xlsx" in summary.warnings[0]
        assert summary.failed == 0
        assert summary.imported == 1


# --------------------------------------------------------------------------- #
# processBidsSubjects (batch import path)                                     #
# --------------------------------------------------------------------------- #

class TestProcessBidsSubjects:
    def test_imported_subject_and_files(self, tmp_path, monkeypatch):
        _stub_add_file_ok(monkeypatch)
        dataset = str(tmp_path / "dataset")
        src = _make_source_file(tmp_path)
        conn = RecordingConn()

        processBidsSubjects(conn, dataset, [
            {"subject_id": "batch01", "files": [{"file_path": src, "modality": "ieeg (ieeg)"}]},
        ])

        summary = conn.summary
        assert isinstance(summary, ImportSummary)
        assert summary.subjects_created == 1
        assert summary.imported == 1
        assert 100 in conn.progress_values

    def test_existing_subject_race_is_skipped(self, tmp_path, monkeypatch):
        _stub_add_file_ok(monkeypatch)
        dataset = _make_dataset_with_subject(tmp_path, "dup01")
        src = _make_source_file(tmp_path)
        conn = RecordingConn()

        processBidsSubjects(conn, dataset, [
            {"subject_id": "dup01", "files": [{"file_path": src, "modality": "ieeg (ieeg)"}]},
        ], overwrite_existing=False)

        summary = conn.summary
        assert summary.subjects_created == 0
        assert summary.skipped == 1
        skipped = summary.items[0]
        assert skipped.subject == "dup01"
        assert skipped.path is None
        assert "already exists" in skipped.reason
        # Progress still reaches 100 despite the whole subject being skipped.
        assert 100 in conn.progress_values

    def test_invalid_subject_id_reason_is_real_cause(self, tmp_path, monkeypatch):
        # add_bids_subject raises ValueError for BOTH "already exists" and a
        # schema-invalid id; the reason must be str(e), never a hard-coded label.
        def raise_invalid(self, subject_id, subject_description, overwrite=False):
            raise ValueError(f"Invalid subject ID '{subject_id}' according to BIDS schema")
        monkeypatch.setattr(BidsFolder, "add_bids_subject", raise_invalid)

        dataset = str(tmp_path / "dataset")
        src = _make_source_file(tmp_path)
        conn = RecordingConn()

        processBidsSubjects(conn, dataset, [
            {"subject_id": "bad", "files": [{"file_path": src, "modality": "ieeg (ieeg)"}]},
        ])

        summary = conn.summary
        assert summary.skipped == 1
        assert "Invalid subject ID" in summary.items[0].reason
        assert "already exists" not in summary.items[0].reason

    def test_partial_subject_and_empty_shell_side_effect(self, tmp_path, monkeypatch):
        # One file converts, one raises: the subject is still created (REQ-GUI-069
        # documents that an all-failed subject leaves an empty shell + tsv row).
        def fake(self, source_path, datatype, entities=None, suffix=None, metadata=None, target_format=None):
            if "bad" in str(source_path):
                raise RuntimeError("conversion failed")
            return {"target_path": str(source_path)}
        monkeypatch.setattr(BidsSubject, "add_file", fake)

        dataset = str(tmp_path / "dataset")
        good = _make_source_file(tmp_path, "good.trc")
        bad = _make_source_file(tmp_path, "bad.trc")
        conn = RecordingConn()

        processBidsSubjects(conn, dataset, [
            {"subject_id": "batch02", "files": [
                {"file_path": good, "modality": "ieeg (ieeg)"},
                {"file_path": bad, "modality": "ieeg (ieeg)"},
            ]},
        ])

        summary = conn.summary
        assert summary.subjects_created == 1
        assert summary.imported == 1
        assert summary.failed == 1
        assert max(conn.progress_values) == 100
