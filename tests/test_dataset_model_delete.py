"""Tests for DatasetModel.delete_files.

PR 8b moved the file-deletion loop out of MainWindow.delete_files_from_tree
(the tree-view "Delete File" action) into the model. The view now only shows
the confirmation and result dialogs; the actual os.remove happens here. These
tests pin the return contract the view relies on: (deleted_paths, failed) where
failed is a list of (path, reason) tuples.
"""

from bidsificator.models.DatasetModel import DatasetModel


def test_delete_files_removes_existing_and_reports_missing(tmp_path):
    existing = tmp_path / "a.edf"
    existing.write_bytes(b"")
    missing = tmp_path / "gone.edf"

    model = DatasetModel()
    deleted, failed = model.delete_files([str(existing), str(missing)])

    assert deleted == [str(existing)]
    assert not existing.exists()
    assert failed == [(str(missing), "File not found")]


def test_delete_files_empty_list_is_noop():
    model = DatasetModel()
    deleted, failed = model.delete_files([])
    assert deleted == []
    assert failed == []


def test_delete_files_does_not_require_loaded_dataset(tmp_path):
    # Deletion is a pure filesystem op; no dataset needs to be loaded.
    f = tmp_path / "x.nii"
    f.write_bytes(b"")

    model = DatasetModel()
    assert not model.is_loaded

    deleted, failed = model.delete_files([str(f)])
    assert deleted == [str(f)]
    assert not f.exists()
    assert failed == []
