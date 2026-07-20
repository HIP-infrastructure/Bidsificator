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
