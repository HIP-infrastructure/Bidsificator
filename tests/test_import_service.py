"""Tests for :class:`ImportService` helpers.

``test_file_detection_modality`` already pins the schema-driven detection path;
this file covers the surrounding pure-Python logic — display-modality mapping
for every datatype branch, acquisition auto-increment, form/data construction,
duplicate detection, per-file validation, and subject preparation.
"""


import pytest

from bidsificator.services.ImportService import ImportService

# --------------------------------------------------------------------------- #
# _display_modality_for_file
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    ("filename", "datatype", "expected"),
    [
        ("rec.png", "ieeg", "photo (ieeg)"),
        ("rec.trc", "ieeg", "ieeg (ieeg)"),
        ("rec.edf", "eeg", "eeg (eeg)"),
        ("scan_t2w.nii", "anat", "T2w (anat)"),
        ("scan_t1rho.nii", "anat", "T1rho (anat)"),
        ("scan_t2star.nii", "anat", "T2* (anat)"),
        ("scan_flair.nii", "anat", "FLAIR (anat)"),
        ("scan_ct.nii", "anat", "CT (anat)"),
        ("scan.nii", "anat", "T1w (anat)"),
        ("rec.nii", "func", "BOLD (func)"),
        ("rec.nii", "dwi", "DWI (dwi)"),
        ("rec.nii", "fmap", "fieldmap (fmap)"),
        ("rec.nii", "perf", "ASL (perf)"),
        ("rec.nii", "beh", "events (beh)"),
        ("rec.xyz", "mystery", "mystery"),  # unknown datatype passes through
    ],
)
def test_display_modality_for_file(filename, datatype, expected):
    assert ImportService._display_modality_for_file(filename, datatype) == expected


# --------------------------------------------------------------------------- #
# get_next_acquisition_number
# --------------------------------------------------------------------------- #

def test_acquisition_starts_at_01_when_none_match():
    assert ImportService.get_next_acquisition_number([], "", "ieeg (ieeg)", "rest") == "01"


def test_acquisition_increments_over_matching_files():
    existing = [
        {"session": "", "modality": "ieeg (ieeg)", "task": "rest", "acquisition": "01"},
        {"session": "", "modality": "ieeg (ieeg)", "task": "rest", "acquisition": "02"},
    ]
    assert ImportService.get_next_acquisition_number(existing, "", "ieeg (ieeg)", "rest") == "03"


def test_acquisition_ignores_non_matching_and_bad_values():
    existing = [
        {"session": "01", "modality": "ieeg (ieeg)", "task": "rest", "acquisition": "05"},  # other session
        {"session": "", "modality": "ieeg (ieeg)", "task": "rest", "acquisition": "oops"},  # not a number
    ]
    assert ImportService.get_next_acquisition_number(existing, "", "ieeg (ieeg)", "rest") == "01"


# --------------------------------------------------------------------------- #
# create_file_data_from_form
# --------------------------------------------------------------------------- #

def test_create_file_data_strips_session_prefix():
    data = ImportService.create_file_data_from_form(
        "/data/rec.trc",
        {"modality": "ieeg (ieeg)", "session": "ses-01", "task": "rest"},
    )
    assert data["file_name"] == "rec.trc"
    assert data["session"] == "01"  # "ses-" prefix stripped for storage
    assert data["modality"] == "ieeg (ieeg)"
    assert data["task"] == "rest"


# --------------------------------------------------------------------------- #
# process_multiple_files edge cases
# --------------------------------------------------------------------------- #

def test_process_rejects_unsupported_extension(tmp_path):
    bogus = tmp_path / "notes.xyz"
    bogus.write_bytes(b"")
    successful, failed = ImportService.process_multiple_files(
        [str(bogus)], {"task": "rest"}, []
    )
    assert successful == []
    assert len(failed) == 1
    assert "Unsupported file type" in failed[0]


def test_process_flags_duplicate_against_existing(tmp_path):
    rec = tmp_path / "rec.trc"
    rec.write_bytes(b"")
    existing = [{"file_path": str(rec)}]
    successful, failed = ImportService.process_multiple_files(
        [str(rec)], {"task": "rest"}, existing
    )
    assert successful == []
    assert len(failed) == 1
    assert "already exists" in failed[0]


# --------------------------------------------------------------------------- #
# validate_file_data / prepare_subject_for_import
# --------------------------------------------------------------------------- #

def test_validate_file_data_missing_field():
    ok, msg = ImportService.validate_file_data({"file_name": "x", "file_path": "/x"})
    assert ok is False
    assert "modality" in msg


def test_validate_file_data_missing_file(tmp_path):
    data = {"file_name": "x.trc", "file_path": str(tmp_path / "gone.trc"), "modality": "ieeg (ieeg)"}
    ok, msg = ImportService.validate_file_data(data)
    assert ok is False
    assert "does not exist" in msg


def test_validate_file_data_ok(tmp_path):
    rec = tmp_path / "rec.trc"
    rec.write_bytes(b"")
    data = {"file_name": "rec.trc", "file_path": str(rec), "modality": "ieeg (ieeg)"}
    ok, msg = ImportService.validate_file_data(data)
    assert ok is True
    assert msg == ""


def test_prepare_subject_drops_invalid_files(tmp_path):
    good = tmp_path / "rec.trc"
    good.write_bytes(b"")
    files = [
        {"file_name": "rec.trc", "file_path": str(good), "modality": "ieeg (ieeg)"},
        {"file_name": "bad", "file_path": str(tmp_path / "gone"), "modality": "ieeg (ieeg)"},
    ]
    result = ImportService.prepare_subject_for_import("sub-01", files)
    assert result["subject_id"] == "sub-01"
    assert len(result["files"]) == 1
    assert result["files"][0]["file_path"] == str(good)
