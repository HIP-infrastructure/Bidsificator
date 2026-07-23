"""Offscreen view tests for the Import Files tab's batch mode (UR-GUI-010).

Drives the real ``QListWidget`` selection transitions on a live ``ImportFilesTab``
(built via ``MainWindow`` like ``test_mainwindow_smoke``) under
``QT_QPA_PLATFORM=offscreen``. The load-bearing check is that ctrl-deselecting a
multi-selection down to one file writes nothing onto that file — the adversarial
review's F1 corruption path (a placeholder form saved over real data).
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
def tab(qapp):
    win = MainWindow()
    yield win._import_files_tab
    win.close()
    win.deleteLater()


def _seed(tab, files):
    tab._import_files_controller.model.file_model.load_from_dicts(files, "sub01")
    tab.refresh_import_file_list()


def _f(name, session, task, acq, modality="ieeg (ieeg)"):
    return {
        "file_name": name,
        "file_path": f"/data/{name}",
        "modality": modality,
        "session": session,
        "task": task,
        "acquisition": acq,
    }


def _select(tab, rows):
    lw = tab.ImportFileListWidget
    lw.clearSelection()
    for r in rows:
        lw.item(r).setSelected(True)


def test_selecting_two_files_enters_batch_mode(tab):
    # Tasks must be real TaskComboBox items so the single-file form round-trips
    # cleanly; only the batch behaviour is under test here.
    _seed(tab, [_f("a.trc", "post", "Seizure", "01"),
                _f("b.trc", "post", "Sleep", "01")])

    _select(tab, [0, 1])

    assert tab._batch_mode is True
    assert tab._batch_indices == [0, 1]
    # Tasks differ -> the Task combo shows the "(multiple values)" placeholder.
    assert tab.TaskComboBox.currentIndex() == -1
    # Modality is shared -> shown directly, not a placeholder.
    assert tab.ModalityComboBox.currentText() == "ieeg (ieeg)"
    # Per-file line-edits are disabled in batch mode.
    assert tab.AcquisitionLineEdit.isEnabled() is False
    assert tab.ContrastAgentLineEdit.isEnabled() is False


def test_multi_to_single_transition_writes_nothing(tab):
    """Ctrl-deselecting from many files down to one must not save the shared
    placeholder form onto the remaining file (adversarial review F1)."""
    _seed(tab, [_f("a.trc", "post", "Seizure", "01"),
                _f("b.trc", "post", "Sleep", "02"),
                _f("c.trc", "post", "Stimulation", "03")])

    # Count model writes so we can prove none happen during the transition.
    model = tab._import_files_controller.model
    calls = {"n": 0}
    original = model.update_selected_file_from_form

    def _counting_save(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    model.update_selected_file_from_form = _counting_save

    _select(tab, [0, 1, 2])          # batch mode; Task shows placeholder
    assert tab._batch_mode is True
    writes_before = calls["n"]

    # Deselect down to a single file (row 0).
    tab.ImportFileListWidget.item(1).setSelected(False)
    tab.ImportFileListWidget.item(2).setSelected(False)

    assert tab._batch_mode is False
    # No form save happened on the way out of batch mode...
    assert calls["n"] == writes_before
    # ...and every file keeps exactly the metadata it was seeded with (no
    # "(multiple values)"/empty placeholder written onto the anchor row).
    files = model.file_model.files
    assert [f.task for f in files] == ["Seizure", "Sleep", "Stimulation"]
    assert [f.session for f in files] == ["post", "post", "post"]


def test_batch_edit_applies_to_all_selected(tab):
    combo = tab.ModalityComboBox
    if combo.count() < 2:
        pytest.skip("need at least two modalities in the dropdown")
    m0, m1 = combo.itemText(0), combo.itemText(1)

    # anat files carry no task; keep task empty so the single-file round-trip is
    # clean and only the modality batch-apply is under test.
    _seed(tab, [_f("a.trc", "post", "", "01", modality=m0),
                _f("b.trc", "post", "", "02", modality=m0),
                _f("c.trc", "post", "", "03", modality=m0)])

    _select(tab, [0, 1, 2])
    assert tab.ModalityComboBox.currentText() == m0  # shared value shown

    # Simulate a user picking a different modality (activated fires on user pick).
    combo.setCurrentIndex(1)
    combo.activated.emit(1)

    assert [f.modality for f in tab._import_files_controller.model.file_model.files] == [m1, m1, m1]
    # The selection survives the edit (no list rebuild) — still batch mode on all 3.
    assert tab._batch_mode is True
    assert tab._batch_indices == [0, 1, 2]


def test_single_edit_between_batches_keeps_acquisition_sequential(tab):
    """End-to-end regression for the user's '2 3 4' report: batch-set session on all,
    single-edit one file's session, reselect all and batch-set back -> acq 01,02,03."""
    _seed(tab, [_f("a.trc", "post", "Seizure", "01"),
                _f("b.trc", "post", "Seizure", "02"),
                _f("c.trc", "post", "Seizure", "03")])
    fm = tab._import_files_controller.model.file_model

    # 1) select all, batch session -> pre
    _select(tab, [0, 1, 2])
    tab._apply_batch_field("session", "ses-pre")

    # 2) keep only the middle file, single-edit its session back to post
    _select(tab, [1])
    tab.SessionComboBox.setEditText("ses-post")
    tab.save_current_form_to_data()

    # 3) reselect all, batch session -> post (the "put it back" step)
    _select(tab, [0, 1, 2])
    tab._apply_batch_field("session", "ses-post")

    assert all(f.session == "post" for f in fm.files)
    assert sorted(f.acquisition for f in fm.files) == ["01", "02", "03"]


def test_single_file_acquisition_updates_live_on_session_change(tab):
    """Changing the session of a single selected file updates the Acquisition field
    immediately — no need to switch to another file and back (REQ-GUI-088)."""
    _seed(tab, [_f("a.trc", "post", "Seizure", "01"),
                _f("b.trc", "post", "Seizure", "02"),
                _f("c.trc", "post", "Seizure", "03")])

    _select(tab, [2])  # single-select the third file (acq 03)
    assert tab.AcquisitionLineEdit.text() == "03"

    # Move it to ses-pre via the dropdown -> alone in the new group -> shows 01 live.
    pre_idx = tab.SessionComboBox.findText("ses-pre")
    tab.SessionComboBox.setCurrentIndex(pre_idx)
    assert tab.AcquisitionLineEdit.text() == "01"

    # Put it back to ses-post -> its original acquisition (03) is shown again.
    post_idx = tab.SessionComboBox.findText("ses-post")
    tab.SessionComboBox.setCurrentIndex(post_idx)
    assert tab.AcquisitionLineEdit.text() == "03"


def test_batch_remove_deletes_all_selected(tab):
    _seed(tab, [_f("a.trc", "post", "Seizure", "01"),
                _f("b.trc", "post", "Seizure", "02"),
                _f("c.trc", "post", "Seizure", "03")])

    _select(tab, [0, 2])  # remove first and last
    tab.remove_file_from_list()

    remaining = [f.file_name for f in tab._import_files_controller.model.file_model.files]
    assert remaining == ["b.trc"]
