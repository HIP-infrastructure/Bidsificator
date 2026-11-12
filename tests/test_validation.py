#!/usr/bin/env python
"""Tests for the schema-driven BIDS ValidationService.

These build tiny datasets under pytest's ``tmp_path`` and assert on the
``ValidationService`` result, rather than pointing at a hardcoded dataset path.
"""

import json

from bidsificator.services.ValidationServiceSchema import ValidationService


def _missing_description_errors(result):
    """Errors flagging a missing dataset_description.json (a BIDS-required file)."""
    return [
        err for err in result.errors
        if "dataset_description.json" in err.message and err.rule == "missing-required-file"
    ]


def test_nonexistent_dataset_is_invalid():
    result = ValidationService().validate_dataset("/this/path/should/not/exist/bidsificator")
    assert result.is_valid is False
    assert result.error_count >= 1
    assert any("does not exist" in err.message.lower() for err in result.errors)


def test_empty_directory_reports_missing_required_files(tmp_path):
    result = ValidationService().validate_dataset(str(tmp_path))
    assert result.is_valid is False
    # An empty directory is missing dataset_description.json, which BIDS requires.
    assert _missing_description_errors(result), (
        "expected a missing-required-file error for dataset_description.json, "
        f"got: {[e.message for e in result.errors]}"
    )


def test_adding_dataset_description_clears_that_error(tmp_path):
    service = ValidationService()

    before = service.validate_dataset(str(tmp_path))
    assert _missing_description_errors(before), (
        "precondition: dataset_description.json should be reported missing"
    )

    (tmp_path / "dataset_description.json").write_text(
        json.dumps({"Name": "Test Dataset", "BIDSVersion": "1.10.1"})
    )

    after = service.validate_dataset(str(tmp_path))
    assert not _missing_description_errors(after), (
        "adding dataset_description.json should clear the missing-required-file error"
    )


# --------------------------------------------------------------------------- #
# multi-part extensions (.nii.gz)
# --------------------------------------------------------------------------- #

def _dataset_with_t1w(root, extension):
    """A minimal dataset holding one synthetic T1w volume and its (empty) JSON sidecar."""
    import nibabel as nib
    import numpy as np

    root.mkdir()
    (root / "dataset_description.json").write_text(
        json.dumps({"Name": "Test Dataset", "BIDSVersion": "1.10.1"})
    )
    anat = root / "sub-01" / "anat"
    anat.mkdir(parents=True)
    volume = nib.Nifti1Image(np.zeros((4, 4, 4), dtype=np.int16), np.eye(4))
    nib.save(volume, str(anat / f"sub-01_T1w{extension}"))
    (anat / "sub-01_T1w.json").write_text("{}")
    return root


def _issues(result, root):
    """(severity, file name, rule) of every reported issue, the data file's extension masked."""
    found = set()
    for issue in result.errors + result.warnings:
        name = issue.path.replace(str(root), "").rsplit("/", 1)[-1]
        name = name.replace("sub-01_T1w.nii.gz", "sub-01_T1w<data>").replace("sub-01_T1w.nii", "sub-01_T1w<data>")
        found.add((issue.severity, name, issue.rule))
    return found


def test_nii_gz_data_file_is_validated_like_nii(tmp_path):
    service = ValidationService()
    plain_root = _dataset_with_t1w(tmp_path / "plain", ".nii")
    gz_root = _dataset_with_t1w(tmp_path / "compressed", ".nii.gz")

    plain = service.validate_dataset(str(plain_root))
    compressed = service.validate_dataset(str(gz_root))

    rules = {issue.rule for issue in compressed.errors + compressed.warnings}
    # '.gz' is not the extension, 'T1w.nii' is not the suffix, and the sidecar exists.
    assert "unexpected-extension" not in rules
    assert "no-validation-rule" not in rules
    assert "missing-sidecar" not in rules
    # The sidecar is found, so its content is checked: an empty T1w sidecar
    # is reported for its missing recommended keys.
    assert any(
        issue.path.endswith("sub-01_T1w.json") and issue.rule.startswith("SIDECAR_KEY_RECOMMENDED")
        for issue in compressed.warnings
    )
    assert _issues(compressed, gz_root) == _issues(plain, plain_root)


def test_validate_filename_reads_suffix_before_multi_part_extension():
    result = ValidationService().validate_filename("sub-01_T1w.nii.gz", "anat")
    assert [issue.rule for issue in result.errors] == []
    assert "no-validation-rule" not in [issue.rule for issue in result.warnings]


def test_parsing_helpers_strip_the_whole_extension():
    from pathlib import Path

    from bidsificator.validation._parsing import (
        extract_suffix_from_filename,
        parse_entities_from_filename,
    )

    assert extract_suffix_from_filename("sub-01_ses-pre_T1w.nii.gz") == "T1w"
    assert extract_suffix_from_filename("sub-01_task-rest_ieeg.edf") == "ieeg"
    assert parse_entities_from_filename(Path("sub-01_ses-pre_T1w.nii.gz")) == {"sub": "01", "ses": "pre"}
