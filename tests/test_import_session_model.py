"""Tests for ImportSessionModel — the single source of truth for the Import Files tab.

After the PR 8a MVC state migration, MainWindow keeps no parallel copy of the
import-file list; it reads and writes the model through ImportFilesController.
These tests pin the model behavior the view now relies on: the form round-trip,
session-prefix handling (the guard behind the #15 acquisition-corruption fix),
the file_path field exposed to the form, selection re-indexing on removal, and
subject propagation.
"""

from bidsificator.models.ImportSessionModel import ImportSessionModel


def _seed(model: ImportSessionModel, paths: list[str], subject: str = "sub01") -> ImportSessionModel:
    files = [
        {"file_name": p.rsplit("/", 1)[-1], "file_path": p, "modality": "ieeg (ieeg)"}
        for p in paths
    ]
    model.file_model.load_from_dicts(files, subject)
    model.selected_file_index = 0
    return model


def test_form_data_includes_file_path_and_prefixed_session():
    model = ImportSessionModel()
    model.file_model.load_from_dicts(
        [{"file_name": "a.edf", "file_path": "/data/a.edf", "modality": "ieeg (ieeg)",
          "session": "post", "task": "rest", "acquisition": "01"}],
        "sub01",
    )
    model.selected_file_index = 0

    form = model.get_form_data_for_selected_file()
    assert form["file_path"] == "/data/a.edf"   # exposed so the view can fill BrowseLineEdit
    assert form["session"] == "ses-post"        # prefixed for display
    assert form["task"] == "rest"
    assert form["acquisition"] == "01"


def test_update_from_form_strips_prefix_and_keeps_empty_session_empty():
    model = ImportSessionModel()
    model.file_model.load_from_dicts(
        [{"file_name": "a.edf", "file_path": "/data/a.edf", "modality": "ieeg (ieeg)"}],
        "sub01",
    )
    model.selected_file_index = 0

    # A user-entered "ses-pre" is stored without the prefix.
    assert model.update_selected_file_from_form(
        {"modality": "ieeg (ieeg)", "session": "ses-pre", "task": "rest",
         "contrast_agent": "", "acquisition": "01", "reconstruction": ""}
    )
    assert model.get_selected_file().session == "pre"

    # An empty session must round-trip as empty — writing a session the user never
    # chose is exactly the #15 acquisition-corruption bug.
    assert model.update_selected_file_from_form(
        {"modality": "ieeg (ieeg)", "session": "", "task": "rest",
         "contrast_agent": "", "acquisition": "01", "reconstruction": ""}
    )
    assert model.get_selected_file().session == ""
    assert model.get_form_data_for_selected_file()["session"] == ""


def test_update_from_form_with_no_selection_is_noop():
    model = ImportSessionModel()
    assert model.selected_file_index == -1
    assert model.update_selected_file_from_form({"modality": "ieeg (ieeg)"}) is False


def test_remove_reindexes_selection_to_the_item_that_took_its_place():
    model = ImportSessionModel()
    _seed(model, ["/d/a.edf", "/d/b.edf", "/d/c.edf"])

    model.selected_file_index = 1
    assert model.remove_selected_file()
    assert model.file_model.count() == 2
    # Selection stays valid and now points at what was the third file.
    assert model.selected_file_index == 1
    assert model.get_selected_file().file_path == "/d/c.edf"


def test_remove_last_file_clears_selection():
    model = ImportSessionModel()
    _seed(model, ["/d/a.edf"])

    assert model.remove_selected_file()
    assert model.file_model.count() == 0
    assert model.selected_file_index == -1
    assert model.get_selected_file() is None


def test_selected_file_index_out_of_range_clamps_to_minus_one():
    model = ImportSessionModel()
    _seed(model, ["/d/a.edf", "/d/b.edf"])

    model.selected_file_index = 5
    assert model.selected_file_index == -1


def test_change_subject_propagates_to_all_files():
    model = ImportSessionModel()
    _seed(model, ["/d/a.edf", "/d/b.edf"], subject="sub01")

    assert model.change_subject("sub02")
    assert model.file_model.current_subject == "sub02"
    assert all(f.intended_subject == "sub02" for f in model.file_model.files)


def test_change_subject_to_empty_is_rejected():
    model = ImportSessionModel()
    _seed(model, ["/d/a.edf"], subject="sub01")

    assert model.change_subject("") is False
    assert model.file_model.current_subject == "sub01"
