"""Model-layer tests for multi-file batch metadata editing (UR-GUI-010).

These exercise the pure logic behind the Import Files tab's batch mode — no Qt:
``ImportFileModel.update_files_fields`` / ``common_value_for`` / the ``MIXED``
sentinel, and ``ImportSessionModel.update_files_from_form`` with its
edited-files-only acquisition reassignment (REQ-GUI-081/082/083). The critical
invariant is that a batch edit never renumbers the acquisition of files the user
did not select (that would silently diverge from what is on disk on re-import).
"""

from bidsificator.models.ImportFileModel import MIXED, ImportFileModel
from bidsificator.models.ImportSessionModel import ImportSessionModel


def _model(files: list[dict], subject: str = "sub01") -> ImportSessionModel:
    model = ImportSessionModel()
    model.file_model.load_from_dicts(files, subject)
    return model


def _f(name, session, task, acq, modality="ieeg (ieeg)"):
    return {
        "file_name": name,
        "file_path": f"/data/{name}",
        "modality": modality,
        "session": session,
        "task": task,
        "acquisition": acq,
    }


# --------------------------------------------------------------------------- #
# update_files_fields (REQ-GUI-081)
# --------------------------------------------------------------------------- #

def test_update_files_fields_applies_only_given_keys():
    fm = ImportFileModel()
    fm.load_from_dicts([_f("a.trc", "post", "Rest", "01"),
                        _f("b.trc", "post", "Rest", "02")], "sub01")

    updated = fm.update_files_fields([0, 1], {"modality": "eeg (eeg)"})

    assert updated == [0, 1]
    # modality changed on both; task left exactly as each had it.
    assert [f.modality for f in fm.files] == ["eeg (eeg)", "eeg (eeg)"]
    assert [f.task for f in fm.files] == ["Rest", "Rest"]


def test_update_files_fields_strips_ses_prefix():
    fm = ImportFileModel()
    fm.load_from_dicts([_f("a.trc", "post", "Rest", "01")], "sub01")

    fm.update_files_fields([0], {"session": "ses-pre"})

    assert fm.get_file(0).session == "pre"  # stored bare, like the single-file path


def test_update_files_fields_ignores_unknown_keys_and_bad_indices():
    fm = ImportFileModel()
    fm.load_from_dicts([_f("a.trc", "post", "Rest", "01")], "sub01")

    updated = fm.update_files_fields([0, 99], {"bogus": "x", "task": "Sleep"})

    assert updated == [0]                       # index 99 skipped
    assert not hasattr(fm.get_file(0), "bogus")  # unknown attr not injected
    assert fm.get_file(0).task == "Sleep"


# --------------------------------------------------------------------------- #
# common_value_for + MIXED (REQ-GUI-082)
# --------------------------------------------------------------------------- #

def test_common_value_for_shared_vs_mixed():
    fm = ImportFileModel()
    fm.load_from_dicts([_f("a.trc", "post", "Rest", "01"),
                        _f("b.trc", "post", "Other", "01")], "sub01")

    assert fm.common_value_for([0, 1], "modality") == "ieeg (ieeg)"  # shared
    assert fm.common_value_for([0, 1], "session") == "post"          # shared, bare
    assert fm.common_value_for([0, 1], "task") is MIXED              # differ


def test_common_value_for_single_index_is_that_value():
    fm = ImportFileModel()
    fm.load_from_dicts([_f("a.trc", "post", "Rest", "01"),
                        _f("b.trc", "pre", "Other", "01")], "sub01")

    assert fm.common_value_for([1], "task") == "Other"


# --------------------------------------------------------------------------- #
# acquisition reassignment (REQ-GUI-083)
# --------------------------------------------------------------------------- #

def test_edited_files_moved_to_new_group_get_sequential_acq():
    # A, B, C share (post, ieeg, Rest): 01/02/03. Edit A+B -> task Seizure.
    model = _model([_f("a.trc", "post", "Rest", "01"),
                    _f("b.trc", "post", "Rest", "02"),
                    _f("c.trc", "post", "Rest", "03")])

    assert model.update_files_from_form([0, 1], {"task": "Seizure"}) is True

    files = model.file_model.files
    # C is untouched — still acq 03 (a legitimate gap in the old group).
    assert files[2].acquisition == "03"
    assert files[2].task == "Rest"
    # A, B are now their own group and numbered cleanly from 01.
    assert files[0].task == "Seizure" and files[1].task == "Seizure"
    assert {files[0].acquisition, files[1].acquisition} == {"01", "02"}


def test_all_selected_moved_to_empty_group_number_in_list_order():
    model = _model([_f("a.trc", "post", "Rest", "01"),
                    _f("b.trc", "post", "Rest", "02"),
                    _f("c.trc", "post", "Rest", "03")])

    model.update_files_from_form([0, 1, 2], {"session": "ses-pre"})

    files = model.file_model.files
    assert all(f.session == "pre" for f in files)
    assert [f.acquisition for f in files] == ["01", "02", "03"]


def test_unchanged_group_key_edit_does_not_bump_acquisition():
    # Editing task to the value files already have must not renumber them.
    model = _model([_f("a.trc", "post", "Rest", "01"),
                    _f("b.trc", "post", "Rest", "02")])

    model.update_files_from_form([0, 1], {"task": "Rest"})

    assert [f.acquisition for f in model.file_model.files] == ["01", "02"]


def test_moving_into_populated_group_continues_after_existing_and_preserves_it():
    # C sits alone in (post, ieeg, Report) with a hand-typed acq 05.
    model = _model([_f("c.trc", "post", "Report", "05"),
                    _f("a.trc", "post", "Rest", "01"),
                    _f("b.trc", "post", "Rest", "02")])

    # Move A, B (indices 1, 2) into C's group.
    model.update_files_from_form([1, 2], {"task": "Report"})

    files = model.file_model.files
    assert files[0].acquisition == "05"      # C untouched, manual value preserved
    assert files[1].acquisition == "06"
    assert files[2].acquisition == "07"


def test_batch_edit_renumbers_all_selected_not_just_movers():
    """Regression: the '2 3 4' bug.

    When a batch edit puts every selected file into one group, a selected file that
    was *already* in that group (didn't move) must still be renumbered with its
    peers — otherwise it keeps a stale acquisition and the movers stack after it
    (2,3,4 instead of 1,2,3). Reproduces: set all to 'pre', single-edit the middle
    one back to 'post', then batch-set all to 'post'.
    """
    model = _model([_f("a.trc", "pre", "Rest", "01"),
                    _f("b.trc", "post", "Rest", "02"),   # already at the target session
                    _f("c.trc", "pre", "Rest", "03")])

    model.update_files_from_form([0, 1, 2], {"session": "ses-post"})

    files = model.file_model.files
    assert all(f.session == "post" for f in files)
    assert sorted(f.acquisition for f in files) == ["01", "02", "03"]


def test_batch_edit_packs_selected_after_unselected_in_same_group():
    """The whole-edited-set renumber must still leave UNSELECTED files untouched."""
    # u is unselected and stays put; a and b are batch-moved into u's group.
    model = _model([_f("u.trc", "post", "Rest", "07"),   # unselected, hand-set acq
                    _f("a.trc", "pre", "Rest", "01"),
                    _f("b.trc", "pre", "Rest", "02")])

    model.update_files_from_form([1, 2], {"session": "ses-post"})

    files = model.file_model.files
    assert files[0].acquisition == "07"              # unselected untouched
    assert {files[1].acquisition, files[2].acquisition} == {"08", "09"}  # packed after it


def test_update_files_from_form_empty_inputs_are_noops():
    model = _model([_f("a.trc", "post", "Rest", "01")])
    assert model.update_files_from_form([], {"task": "X"}) is False
    assert model.update_files_from_form([0], {}) is False
    assert model.file_model.get_file(0).acquisition == "01"


# --------------------------------------------------------------------------- #
# single-file acquisition on group change (REQ-GUI-088) — the same auto-managed
# acquisition rule as batch, applied when one file is moved on its own.
# --------------------------------------------------------------------------- #

def test_single_file_move_to_new_group_resets_acquisition_to_01():
    # 3 files in ses-post (01/02/03); single-move the last to ses-pre.
    model = _model([_f("a.trc", "post", "Rest", "01"),
                    _f("b.trc", "post", "Rest", "02"),
                    _f("c.trc", "post", "Rest", "03")])
    model.selected_file_index = 2

    model.update_selected_file_from_form(
        {"modality": "ieeg (ieeg)", "session": "ses-pre", "task": "Rest",
         "contrast_agent": "", "acquisition": "03", "reconstruction": ""})

    files = model.file_model.files
    assert files[2].session == "pre" and files[2].acquisition == "01"  # alone in new group
    assert [f.acquisition for f in files[:2]] == ["01", "02"]          # unmoved untouched


def test_single_file_move_of_middle_leaves_source_gap():
    model = _model([_f("a.trc", "post", "Rest", "01"),
                    _f("b.trc", "post", "Rest", "02"),
                    _f("c.trc", "post", "Rest", "03")])
    model.selected_file_index = 1  # the middle file

    model.update_selected_file_from_form(
        {"modality": "ieeg (ieeg)", "session": "ses-pre", "task": "Rest",
         "contrast_agent": "", "acquisition": "02", "reconstruction": ""})

    files = model.file_model.files
    assert files[1].session == "pre" and files[1].acquisition == "01"
    # Source group keeps a-01, c-03; the 02 gap is acceptable (same as removal).
    assert files[0].acquisition == "01" and files[2].acquisition == "03"


def test_moving_several_files_one_by_one_pack_into_new_group():
    # Five files in ses-post; hand-move indices 0, 2, 4 to ses-pre one at a time.
    model = _model([_f(f"f{i}.trc", "post", "Rest", f"{i + 1:02d}") for i in range(5)])

    for idx in (0, 2, 4):
        model.selected_file_index = idx
        form = model.get_form_data_for_selected_file()
        form["session"] = "ses-pre"
        model.update_selected_file_from_form(form)

    pre = [f.acquisition for f in model.file_model.files if f.session == "pre"]
    assert sorted(pre) == ["01", "02", "03"]  # packed in move order


def test_single_file_same_group_edit_preserves_entered_acquisition():
    # No group-key change -> the acquisition entered in the form is kept as-is.
    model = _model([_f("a.trc", "post", "Rest", "01"),
                    _f("b.trc", "post", "Rest", "02")])
    model.selected_file_index = 1

    model.update_selected_file_from_form(
        {"modality": "ieeg (ieeg)", "session": "ses-post", "task": "Rest",
         "contrast_agent": "", "acquisition": "07", "reconstruction": "x"})

    assert model.file_model.files[1].acquisition == "07"


# --------------------------------------------------------------------------- #
# preview_acquisition — read-only, drives the live single-file display
# --------------------------------------------------------------------------- #

def test_preview_acquisition_same_group_returns_files_own_value():
    fm = ImportFileModel()
    fm.load_from_dicts([_f("a.trc", "post", "Rest", "01"),
                        _f("b.trc", "post", "Rest", "02")], "sub01")
    assert fm.preview_acquisition(1, "ses-post", "ieeg (ieeg)", "Rest") == "02"


def test_preview_acquisition_new_group_returns_next_and_does_not_mutate():
    fm = ImportFileModel()
    fm.load_from_dicts([_f("a.trc", "post", "Rest", "01"),
                        _f("b.trc", "post", "Rest", "02"),
                        _f("c.trc", "post", "Rest", "03")], "sub01")
    # Moving c on its own to ses-pre -> alone in that group -> 01.
    assert fm.preview_acquisition(2, "ses-pre", "ieeg (ieeg)", "Rest") == "01"
    assert fm.get_file(2).acquisition == "03"  # read-only: nothing changed
