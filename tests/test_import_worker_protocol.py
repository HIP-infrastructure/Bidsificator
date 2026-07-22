"""Round-trip smoke tests for the QThread import workers (UR-GUI-009 ticket 2).

Each test starts the *real* worker, which spawns a real ``multiprocessing.Process``
(the macOS default start method is ``spawn``), and asserts the terminal
``ImportSummary`` survives the pickle boundary and is delivered via the renamed
``import_finished`` signal. A queued file that is missing on disk is used so the
child records a skip without doing any real neuroimaging conversion. The
message-classification logic itself is unit-tested in ``test_import_processor.py``.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.core.BidsFolder import BidsFolder
from bidsificator.workers.import_processor import ImportSummary
from bidsificator.workers.ImportBidsFilesWorker import ImportBidsFilesWorker
from bidsificator.workers.ImportBidsSubjectsWorker import ImportBidsSubjectsWorker


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _run_worker(qapp, worker):
    """Start a worker, wait for the child, and return (summaries, errors)."""
    summaries = []
    errors = []
    worker.import_finished.connect(summaries.append)
    worker.error.connect(errors.append)
    worker.start()
    assert worker.wait(60000), "worker thread did not finish within 60s"
    qapp.processEvents()
    return summaries, errors


def test_files_worker_delivers_summary_across_spawn(qapp, tmp_path):
    dataset = tmp_path / "dataset"
    folder = BidsFolder(str(dataset))
    folder.add_bids_subject("test01", {"age": 25, "sex": "M"})
    folder.generate_participants_tsv()

    worker = ImportBidsFilesWorker(
        str(dataset), "test01",
        [{"file_path": str(tmp_path / "missing.trc"), "modality": "ieeg (ieeg)"}],
    )
    summaries, errors = _run_worker(qapp, worker)

    assert errors == []
    assert len(summaries) == 1
    summary = summaries[0]
    assert isinstance(summary, ImportSummary)  # unpickled intact across spawn
    assert summary.skipped == 1
    assert summary.imported == 0
    assert "not found" in summary.items[0].reason


def test_subjects_worker_delivers_summary_across_spawn(qapp, tmp_path):
    dataset = tmp_path / "dataset"

    worker = ImportBidsSubjectsWorker(
        str(dataset),
        [{"subject_id": "batch01",
          "files": [{"file_path": str(tmp_path / "missing.trc"), "modality": "ieeg (ieeg)"}]}],
    )
    summaries, errors = _run_worker(qapp, worker)

    assert errors == []
    assert len(summaries) == 1
    summary = summaries[0]
    assert isinstance(summary, ImportSummary)
    assert summary.subjects_created == 1
    assert summary.skipped == 1
    assert summary.imported == 0
