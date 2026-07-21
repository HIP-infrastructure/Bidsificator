"""Tests for :class:`SubjectLookupService` — CSV lookup-table parsing and name mapping.

The service is pure Python (all static methods), so these tests use ``tmp_path``
CSV fixtures and need no Qt or filesystem beyond the temp dir. They pin the
numeric/CUSTOM parsing modes, the per-line validation error messages, the
case-insensitive matching variants, and the template generation helpers.
"""

from pathlib import Path

from bidsificator.services.SubjectLookupService import SubjectLookupService


def _write_csv(tmp_path: Path, content: str, name: str = "lookup.csv") -> str:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


# --------------------------------------------------------------------------- #
# parse_lookup_table
# --------------------------------------------------------------------------- #

def test_parse_missing_file_reports_error():
    mapping, errors = SubjectLookupService.parse_lookup_table("/no/such/file.csv")
    assert mapping == {}
    assert errors == ["CSV file does not exist"]


def test_parse_empty_path_reports_error():
    mapping, errors = SubjectLookupService.parse_lookup_table("")
    assert mapping == {}
    assert errors == ["CSV file does not exist"]


def test_parse_invalid_headers(tmp_path):
    path = _write_csv(tmp_path, "A;B;C\nx;1;2\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert mapping == {}
    assert len(errors) == 1
    assert "Invalid headers" in errors[0]


def test_parse_numeric_mode_maps_and_stores_case_variants(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat_44;1;123\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert errors == []
    # Numeric mode formats as ZZZXXXX.
    assert mapping["Pat_44"] == "0010123"
    # Case variants are stored so Pat_44 / PAT_44 / pat_44 all match.
    assert mapping["pat_44"] == "0010123"
    assert mapping["PAT_44"] == "0010123"


def test_parse_custom_mode_uses_subject_id_verbatim(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat_1;CUSTOM;CHUV001\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert errors == []
    assert mapping["Pat_1"] == "CHUV001"


def test_parse_comma_delimiter_autodetected(tmp_path):
    path = _write_csv(tmp_path, "FolderID,CenterID,SubjectID\nPat,2,7\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert errors == []
    assert mapping["Pat"] == "0020007"


def test_parse_empty_folder_id(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\n;1;123\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert mapping == {}
    assert errors == ["Line 2: Empty FolderID"]


def test_parse_missing_center_or_subject(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat;;123\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert mapping == {}
    assert "Missing CenterID or SubjectID" in errors[0]


def test_parse_non_numeric_center(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat;abc;123\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert mapping == {}
    assert "CenterID must be numeric" in errors[0]


def test_parse_center_out_of_range(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat;1000;123\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert mapping == {}
    assert "CenterID must be 0-999" in errors[0]


def test_parse_non_numeric_subject(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat;1;abc\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert mapping == {}
    assert "SubjectID must be numeric" in errors[0]


def test_parse_subject_out_of_range(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat;1;10000\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert mapping == {}
    assert "SubjectID must be 0-9999" in errors[0]


def test_parse_custom_non_alphanumeric_subject(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat;CUSTOM;CH UV\n")
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert mapping == {}
    assert "alphanumeric only" in errors[0]


def test_parse_duplicate_folder_id_case_insensitive(tmp_path):
    path = _write_csv(
        tmp_path,
        "FolderID;CenterID;SubjectID\nPat_1;1;1\nPAT_1;1;2\n",
    )
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    # First row succeeds; the case-variant duplicate is rejected.
    assert mapping["Pat_1"] == "0010001"
    assert any("Duplicate FolderID" in e for e in errors)


def test_parse_duplicate_subject_name(tmp_path):
    path = _write_csv(
        tmp_path,
        "FolderID;CenterID;SubjectID\nPat_1;1;1\nPat_2;1;1\n",
    )
    mapping, errors = SubjectLookupService.parse_lookup_table(path)
    assert mapping["Pat_1"] == "0010001"
    assert "Pat_2" not in mapping
    assert any("Duplicate subject name" in e for e in errors)


# --------------------------------------------------------------------------- #
# format_subject_name
# --------------------------------------------------------------------------- #

def test_format_subject_name_zero_padding():
    assert SubjectLookupService.format_subject_name(1, 123) == "0010123"
    assert SubjectLookupService.format_subject_name(239, 789) == "2390789"


def test_format_subject_name_rejects_out_of_range():
    assert SubjectLookupService.format_subject_name(-1, 0) == ""
    assert SubjectLookupService.format_subject_name(1000, 0) == ""
    assert SubjectLookupService.format_subject_name(0, -1) == ""
    assert SubjectLookupService.format_subject_name(0, 10000) == ""


# --------------------------------------------------------------------------- #
# validate_csv_format
# --------------------------------------------------------------------------- #

def test_validate_no_path():
    ok, errors = SubjectLookupService.validate_csv_format("")
    assert ok is False
    assert errors == ["No file path provided"]


def test_validate_missing_file():
    ok, errors = SubjectLookupService.validate_csv_format("/no/such.csv")
    assert ok is False
    assert errors == ["File does not exist"]


def test_validate_wrong_extension(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\n", name="lookup.json")
    ok, errors = SubjectLookupService.validate_csv_format(path)
    assert ok is False
    assert "must be a .csv or .txt" in errors[0]


def test_validate_not_delimited(tmp_path):
    path = _write_csv(tmp_path, "just a header line\n")
    ok, errors = SubjectLookupService.validate_csv_format(path)
    assert ok is False
    assert "properly delimited" in errors[0]


def test_validate_missing_headers(tmp_path):
    path = _write_csv(tmp_path, "a;b;c\n")
    ok, errors = SubjectLookupService.validate_csv_format(path)
    assert ok is False
    assert any("expected headers" in e for e in errors)


def test_validate_valid_header(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat;1;1\n")
    ok, errors = SubjectLookupService.validate_csv_format(path)
    assert ok is True
    assert errors == []


# --------------------------------------------------------------------------- #
# get_mapping_preview
# --------------------------------------------------------------------------- #

def test_preview_returns_mappings(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat;1;1\n")
    preview, errors = SubjectLookupService.get_mapping_preview(path)
    assert errors == []
    assert ("Pat", "0010001") in preview


def test_preview_respects_limit(tmp_path):
    path = _write_csv(tmp_path, "FolderID;CenterID;SubjectID\nPat;1;1\n")
    preview, errors = SubjectLookupService.get_mapping_preview(path, limit=1)
    assert errors == []
    assert len(preview) == 1


def test_preview_propagates_errors(tmp_path):
    path = _write_csv(tmp_path, "A;B;C\n")
    preview, errors = SubjectLookupService.get_mapping_preview(path)
    assert preview == []
    assert errors


# --------------------------------------------------------------------------- #
# template generation / saving
# --------------------------------------------------------------------------- #

def test_generate_template_default_has_examples():
    content = SubjectLookupService.generate_template_csv()
    assert content.startswith("FolderID;CenterID;SubjectID")
    assert "CUSTOM" in content


def test_generate_template_with_subject_ids():
    content = SubjectLookupService.generate_template_csv(["A", "B"])
    lines = content.splitlines()
    assert lines[0] == "FolderID;CenterID;SubjectID"
    assert lines[1] == "A;000;0001"
    assert lines[2] == "B;000;0002"


def test_save_template_success(tmp_path):
    target = str(tmp_path / "out.csv")
    ok, msg = SubjectLookupService.save_template_to_file("hello", target)
    assert ok is True
    assert msg == ""
    assert Path(target).read_text(encoding="utf-8") == "hello"


def test_save_template_to_directory_fails(tmp_path):
    # Writing to an existing directory path raises an OSError, handled gracefully.
    ok, msg = SubjectLookupService.save_template_to_file("x", str(tmp_path))
    assert ok is False
    assert "error" in msg.lower()


def test_create_template_file_end_to_end(tmp_path):
    target = str(tmp_path / "template.csv")
    ok, msg = SubjectLookupService.create_template_file(target)
    assert ok is True
    assert msg == ""
    content = Path(target).read_text(encoding="utf-8")
    assert content.startswith("FolderID;CenterID;SubjectID")
