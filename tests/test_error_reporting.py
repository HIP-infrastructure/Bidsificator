"""Regression tests for the silent-``except`` audit.

Each test forces the failure a handler used to swallow and asserts what must
now be observable: the log record (with its traceback), the fallback value the
caller still gets, and - for the three behaviour changes - the dialog, the
validation-report entry or the in-memory state.

All data is synthetic and built under pytest's ``tmp_path``.
"""

import json
import logging
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from bidsificator.controllers.DatasetController import DatasetController
from bidsificator.controllers.PatientTableController import PatientTableController
from bidsificator.core.BidsFolder import BidsFolder
from bidsificator.models.DatasetModel import DatasetModel
from bidsificator.services.ValidationServiceSchema import ValidationService
from bidsificator.validation.report import INTERNAL_ERROR_RULE
from bidsificator.validation.rules_files import FileRuleValidator
from bidsificator.validation.rules_metadata import MetadataRuleValidator


def _internal(issues):
    """Report entries saying that a check itself crashed."""
    return [i for i in issues if i.rule.startswith(INTERNAL_ERROR_RULE)]


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def dataset(qapp, tmp_path):
    """Path of a fresh dataset holding subjects 01 and 02."""
    ok, path = DatasetController().create_new_dataset(str(tmp_path), "demo")
    assert ok, path
    ptc = PatientTableController(lambda: path)
    assert ptc.load_subjects(path) is True
    assert ptc.create_subject("01")[0] is True
    assert ptc.create_subject("02")[0] is True
    return path


def _boom(*_args, **_kwargs):
    raise RuntimeError("synthetic failure")


def _denied(*_args, **_kwargs):
    raise PermissionError("synthetic: permission denied")


def _tracebacks(caplog, logger_suffix):
    """Log records carrying a traceback from the module ending in ``logger_suffix``."""
    return [r for r in caplog.records if r.name.endswith(logger_suffix) and r.exc_info]


# --------------------------------------------------------------------------- #
# Failed subject delete
# --------------------------------------------------------------------------- #

def test_failed_folder_removal_keeps_subject_in_bids_folder(dataset, monkeypatch):
    folder = BidsFolder(dataset)
    monkeypatch.setattr("bidsificator.core.BidsFolder.shutil.rmtree", _denied)

    with pytest.raises(PermissionError):
        folder.delete_bids_subject("01")

    # The folder is still on disk, so the subject must still be known in memory.
    assert (Path(dataset) / "sub-01").is_dir()
    assert folder.subject_exists("01") is True


def test_controller_logs_failed_delete(dataset, monkeypatch, caplog):
    ptc = PatientTableController(lambda: dataset)
    assert ptc.load_subjects(dataset) is True
    deleted = []
    ptc.subject_deleted.connect(deleted.append)
    monkeypatch.setattr("bidsificator.core.BidsFolder.shutil.rmtree", _denied)

    with caplog.at_level(logging.ERROR):
        assert ptc.delete_subject("01") is False

    assert deleted == []
    assert _tracebacks(caplog, "PatientTableController")


def test_table_menu_delete_failure_shows_warning(dataset, monkeypatch):
    from bidsificator.ui import PatientTableWidget as widget_module

    widget = widget_module.PatientTableWidget()
    widget.initialize_controller(lambda: dataset)
    widget.LoadSubjectsInTableWidget(dataset)
    assert widget.item(0, 0).text() == "01"
    widget._selected_item = widget.model().index(0, 0)  # what the context menu records

    shown = []
    monkeypatch.setattr(
        widget_module.QMessageBox, "warning",
        lambda _parent, title, message: shown.append((title, message)),
    )
    monkeypatch.setattr("bidsificator.core.BidsFolder.shutil.rmtree", _denied)

    widget._delete_selected_subject()

    assert len(shown) == 1
    assert "01" in shown[0][1]
    assert (Path(dataset) / "sub-01").is_dir()


def test_subject_whose_folder_is_already_gone_can_still_be_removed(dataset):
    import shutil

    ptc = PatientTableController(lambda: dataset)
    assert ptc.load_subjects(dataset) is True
    shutil.rmtree(Path(dataset) / "sub-01")  # removed outside the application, dataset open
    deleted = []
    ptc.subject_deleted.connect(deleted.append)

    assert ptc.delete_subject("01") is True

    assert deleted == ["01"]
    assert "sub-01" not in (Path(dataset) / "participants.tsv").read_text()


def test_table_menu_delete_success_shows_no_warning(dataset, monkeypatch):
    from bidsificator.ui import PatientTableWidget as widget_module

    widget = widget_module.PatientTableWidget()
    widget.initialize_controller(lambda: dataset)
    widget.LoadSubjectsInTableWidget(dataset)
    widget._selected_item = widget.model().index(0, 0)
    shown = []
    monkeypatch.setattr(widget_module.QMessageBox, "warning", lambda *a: shown.append(a))

    widget._delete_selected_subject()

    assert shown == []
    assert not (Path(dataset) / "sub-01").exists()


# --------------------------------------------------------------------------- #
# Validator checks that crash are reported, not silently passed
# --------------------------------------------------------------------------- #

def _ieeg_dataset(root: Path) -> Path:
    (root / "dataset_description.json").write_text(json.dumps({"Name": "Synthetic", "BIDSVersion": "1.10.1"}))
    ieeg = root / "sub-01" / "ses-01" / "ieeg"
    ieeg.mkdir(parents=True)
    (ieeg / "sub-01_ses-01_task-rest_ieeg.edf").write_bytes(b"0" * 64)
    (ieeg / "sub-01_ses-01_task-rest_ieeg.json").write_text(json.dumps({"TaskName": "rest"}))
    return root


def test_crashed_association_check_is_reported_as_warning(tmp_path, monkeypatch, caplog):
    root = _ieeg_dataset(tmp_path)
    monkeypatch.setattr(FileRuleValidator, "_file_matches_association_selectors", _boom)

    with caplog.at_level(logging.ERROR):
        result = ValidationService().validate_dataset(str(root))

    reported = _internal(result.warnings)
    assert len(reported) == 1
    assert reported[0].path.endswith("sub-01_ses-01_task-rest_ieeg.edf")
    assert reported[0].severity == "warning"
    assert reported[0].rule == "validator-internal-error (associated files)"
    assert "RuntimeError: synthetic failure" in reported[0].message  # readable without the log
    assert _internal(result.errors) == []
    assert _tracebacks(caplog, "rules_files")


def test_association_check_reports_nothing_internal_when_it_runs(tmp_path):
    result = ValidationService().validate_dataset(str(_ieeg_dataset(tmp_path)))

    assert _internal(result.warnings + result.errors) == []
    # The check itself still runs: an iEEG recording without channels.tsv is an error.
    assert [e for e in result.errors if e.rule == "missing-channels"]


def _bold_dataset(root: Path) -> Path:
    (root / "dataset_description.json").write_text(json.dumps({"Name": "Synthetic", "BIDSVersion": "1.10.1"}))
    func = root / "sub-01" / "func"
    func.mkdir(parents=True)
    (func / "sub-01_task-rest_bold.nii").write_bytes(b"not a real volume")
    (func / "sub-01_task-rest_bold.json").write_text(
        json.dumps({"TaskName": "rest", "RepetitionTime": 2.0, "SliceTiming": [0.0, 1.0]})
    )
    return root


def test_crashed_slicetiming_check_is_reported_as_warning(tmp_path, monkeypatch, caplog):
    root = _bold_dataset(tmp_path)
    real_exists = Path.exists

    def exists(self, *args, **kwargs):
        if self.name.endswith(".nii.gz"):
            raise OSError("synthetic: cannot stat")
        return real_exists(self, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", exists)

    with caplog.at_level(logging.ERROR):
        result = ValidationService().validate_dataset(str(root))

    reported = _internal(result.warnings)
    assert len(reported) == 1
    assert reported[0].path.endswith("sub-01_task-rest_bold.json")
    assert reported[0].rule == "validator-internal-error (SliceTiming)"
    assert "OSError: synthetic: cannot stat" in reported[0].message
    assert _tracebacks(caplog, "rules_metadata")


def test_unreadable_nifti_skips_slicetiming_with_a_log(tmp_path, caplog):
    root = _bold_dataset(tmp_path)  # the .nii holds garbage nibabel cannot load

    with caplog.at_level(logging.WARNING):
        result = ValidationService().validate_dataset(str(root))

    assert _internal(result.warnings) == []
    assert not [w for w in result.warnings if w.rule == "SLICETIMING_ELEMENTS"]
    records = _tracebacks(caplog, "rules_metadata")
    assert records and all(r.levelno == logging.WARNING for r in records)
    assert "sub-01_task-rest_bold.nii" in records[0].getMessage()


# --------------------------------------------------------------------------- #
# Validator schema helpers keep their fallback but log the failure
# --------------------------------------------------------------------------- #

class _BrokenSchema:
    """A schema whose raw content cannot be read."""

    @property
    def _raw_schema(self):
        raise RuntimeError("synthetic: schema unavailable")


@pytest.mark.parametrize("method, args, fallback", [
    ("_find_matching_file_rule", ("anat", "T1w"), None),
    ("_get_required_files_from_schema", (), ["dataset_description.json"]),
    ("_get_recommended_file_groups_from_schema", (),
     [("README", "README.md"), ("participants.tsv",), ("CHANGES", "CHANGES.md")]),
])
def test_file_rule_schema_helpers_log_and_fall_back(method, args, fallback, caplog):
    rules = FileRuleValidator(_BrokenSchema(), None, None)

    with caplog.at_level(logging.ERROR):
        assert getattr(rules, method)(*args) == fallback

    assert _tracebacks(caplog, "rules_files")


def test_allowed_root_items_helper_logs_and_falls_back(caplog):
    rules = FileRuleValidator(_BrokenSchema(), None, None)

    with caplog.at_level(logging.ERROR):
        allowed = rules._get_allowed_root_items_from_schema()

    assert {"sourcedata", "derivatives", "code"} <= allowed
    assert _tracebacks(caplog, "rules_files")


@pytest.mark.parametrize("method, args, fallback", [
    ("_get_context_specific_metadata_requirements", ("anat", "T1w", {}), ([], [])),
    ("_datatype_belongs_to_modality", ("anat", "mri"), False),
    ("_get_field_description", ("TaskName",), None),
])
def test_metadata_rule_schema_helpers_log_and_fall_back(method, args, fallback, caplog):
    rules = MetadataRuleValidator(_BrokenSchema())

    with caplog.at_level(logging.ERROR):
        assert getattr(rules, method)(*args) == fallback

    assert _tracebacks(caplog, "rules_metadata")


def test_selector_that_cannot_be_evaluated_is_logged(schema_manager, monkeypatch, caplog):
    rules = MetadataRuleValidator(schema_manager)
    monkeypatch.setattr(MetadataRuleValidator, "_evaluate_selector", _boom)

    with caplog.at_level(logging.WARNING):
        assert rules._matches_sidecar_selectors(['suffix == "bold"'], "func", "bold") is False

    records = _tracebacks(caplog, "rules_metadata")
    assert records and 'suffix == "bold"' in records[0].getMessage()


def test_surfaced_validator_read_errors_keep_their_traceback(tmp_path, monkeypatch, caplog):
    """participants.tsv / dataset_description.json read failures still reach the
    report, and the log now holds the traceback."""
    (tmp_path / "dataset_description.json").write_text(json.dumps({"Name": "x", "BIDSVersion": "1.10.1"}))
    (tmp_path / "participants.tsv").write_bytes(b"participant_id\n\xff\xfe\n")  # not UTF-8
    monkeypatch.setattr("bidsificator.validation.rules_metadata.json.load", _boom)

    with caplog.at_level(logging.ERROR):
        result = ValidationService().validate_dataset(str(tmp_path))

    assert [e for e in result.errors if e.rule == "tsv-read-error"]
    assert [e for e in result.errors if e.rule == "file-read-error"]
    assert _tracebacks(caplog, "rules_files")
    assert _tracebacks(caplog, "rules_metadata")


# --------------------------------------------------------------------------- #
# DatasetModel
# --------------------------------------------------------------------------- #

def test_load_subjects_logs_real_failure_and_falls_back_to_scan(dataset, monkeypatch, caplog):
    monkeypatch.setattr(BidsFolder, "get_bids_subjects", _boom)
    model = DatasetModel()

    with caplog.at_level(logging.ERROR):
        ok, message = model.load_dataset(dataset)

    assert ok, message
    assert sorted(model.subjects) == ["01", "02"]  # directory-scan fallback
    assert _tracebacks(caplog, "DatasetModel")


def test_load_dataset_without_subjects_logs_no_error(qapp, tmp_path, caplog):
    ok, path = DatasetController().create_new_dataset(str(tmp_path), "empty")
    assert ok, path
    model = DatasetModel()

    with caplog.at_level(logging.WARNING):
        ok, message = model.load_dataset(path)

    assert ok, message
    assert model.subjects == []
    assert [r for r in caplog.records if r.name.endswith("DatasetModel")] == []


def test_unreadable_dataset_description_is_logged_and_keeps_folder_name(dataset, caplog):
    (Path(dataset) / "dataset_description.json").write_text("{not json")
    model = DatasetModel()

    with caplog.at_level(logging.WARNING):
        ok, message = model.load_dataset(dataset)

    assert ok, message
    assert model.current_dataset.name == Path(dataset).name
    assert _tracebacks(caplog, "DatasetModel")


@pytest.mark.parametrize("content", ["null", "5", '"a name"', "[1, 2]"])
def test_dataset_description_that_is_not_an_object_still_loads(dataset, content, caplog):
    (Path(dataset) / "dataset_description.json").write_text(content)
    model = DatasetModel()

    with caplog.at_level(logging.WARNING):
        ok, message = model.load_dataset(dataset)

    assert ok, message
    assert model.current_dataset.name == Path(dataset).name
    assert model.current_dataset.description == {}
    assert [r for r in caplog.records if r.name.endswith("DatasetModel") and r.levelno == logging.WARNING]


def test_create_dataset_failure_message_and_traceback(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(BidsFolder, "create_folders", _boom)

    with caplog.at_level(logging.ERROR):
        ok, message = DatasetModel().create_dataset(str(tmp_path), "demo")

    assert ok is False
    assert message == "Failed to create dataset: synthetic failure"
    assert _tracebacks(caplog, "DatasetModel")


def test_delete_files_unexpected_error_is_reported_and_logged(dataset, tmp_path, monkeypatch, caplog):
    victim = tmp_path / "victim.txt"
    victim.write_text("x")
    model = DatasetModel()
    assert model.load_dataset(dataset)[0]
    monkeypatch.setattr(os, "remove", _boom)

    with caplog.at_level(logging.ERROR):
        deleted, failed = model.delete_files([str(victim)])

    assert deleted == []
    assert failed == [(str(victim), "synthetic failure")]
    assert _tracebacks(caplog, "DatasetModel")


# --------------------------------------------------------------------------- #
# Controllers and services that already tell the user: the traceback is kept
# --------------------------------------------------------------------------- #

def test_validation_crash_reaches_user_and_log(dataset, monkeypatch, caplog):
    controller = DatasetController()
    assert controller.load_existing_dataset(dataset)[0]
    failures = []
    controller.operation_failed.connect(lambda *a: failures.append(a))
    monkeypatch.setattr(ValidationService, "validate_dataset", _boom)

    with caplog.at_level(logging.ERROR):
        ok, message = controller.validate_dataset()

    assert ok is False
    assert failures == [("Validation Error", "An error occurred during validation: synthetic failure")]
    assert _tracebacks(caplog, "DatasetController")


def test_create_subject_unexpected_error_reaches_caller_and_log(dataset, monkeypatch, caplog):
    ptc = PatientTableController(lambda: dataset)
    assert ptc.load_subjects(dataset) is True
    monkeypatch.setattr(BidsFolder, "generate_participants_tsv", _boom)

    with caplog.at_level(logging.ERROR):
        ok, message = ptc.create_subject("03")

    assert (ok, message) == (False, "Failed to create subject: synthetic failure")
    assert _tracebacks(caplog, "PatientTableController")


def test_save_options_failure_is_logged(tmp_path, monkeypatch, caplog):
    from bidsificator.controllers.OptionController import OptionController
    from bidsificator.core.OptionFile import OptionFile

    controller = OptionController(str(tmp_path / "config.yaml"))
    monkeypatch.setattr(OptionFile, "save", _denied)

    with caplog.at_level(logging.ERROR):
        assert controller.save_configuration() is False

    assert _tracebacks(caplog, "OptionController")


def test_lookup_table_unexpected_read_error_is_reported_and_logged(tmp_path, monkeypatch, caplog):
    from bidsificator.services.SubjectLookupService import SubjectLookupService

    table = tmp_path / "lookup.csv"
    table.write_text("FolderID;CenterID;SubjectID\nfolder_a;1;1\n")
    monkeypatch.setattr("builtins.open", _boom)

    with caplog.at_level(logging.ERROR):
        mapping, errors = SubjectLookupService.parse_lookup_table(str(table))
        valid, format_errors = SubjectLookupService.validate_csv_format(str(table))
        saved, save_error = SubjectLookupService.save_template_to_file("x", str(tmp_path / "out.csv"))

    assert errors == ["Error reading CSV file: synthetic failure"]
    assert (valid, format_errors) == (False, ["Error reading file: synthetic failure"])
    assert (saved, save_error) == (False, "Unexpected error: synthetic failure")
    logged = " ".join(r.getMessage() for r in _tracebacks(caplog, "SubjectLookupService"))
    assert "Failed to read lookup table" in logged
    assert "Failed to check the format" in logged
    assert "Failed to write lookup table template" in logged


def test_add_files_unexpected_error_is_reported_and_logged(tmp_path, monkeypatch, caplog):
    from bidsificator.services.ImportService import ImportService

    source = tmp_path / "scan.nii"
    source.write_bytes(b"0")
    monkeypatch.setattr(ImportService, "_is_duplicate_file", _boom)

    with caplog.at_level(logging.ERROR):
        result = ImportService.process_multiple_files([str(source)], {}, [])

    assert result[1] == ["scan.nii: synthetic failure"]
    assert _tracebacks(caplog, "ImportService")


# --------------------------------------------------------------------------- #
# Converters and sidecar generation
# --------------------------------------------------------------------------- #

def test_dicom_probe_of_non_dicom_file_is_quiet(tmp_path, caplog):
    from bidsificator.converters.dicom_to_nifti import DicomToNiftiConverter

    plain = tmp_path / "notes"
    plain.write_text("just text, not DICOM")

    with caplog.at_level(logging.DEBUG):
        assert DicomToNiftiConverter().can_convert(plain) is False
        assert DicomToNiftiConverter().can_convert(tmp_path) is False

    assert [r for r in caplog.records if r.name.endswith("dicom_to_nifti") and r.levelno >= logging.WARNING] == []


def test_dicom_probe_unexpected_error_is_logged(tmp_path, monkeypatch, caplog):
    from bidsificator.converters import dicom_to_nifti

    plain = tmp_path / "scan.dcm"
    plain.write_bytes(b"0")
    monkeypatch.setattr(dicom_to_nifti.pydicom, "dcmread", _boom)

    with caplog.at_level(logging.ERROR):
        assert dicom_to_nifti.DicomToNiftiConverter().can_convert(plain) is False

    assert _tracebacks(caplog, "dicom_to_nifti")


def test_events_json_falls_back_to_default_columns_with_a_log(tmp_path, schema_manager, caplog):
    from bidsificator.core.BidsSubjectSchema import BidsSubject

    subject = BidsSubject("01", tmp_path, schema_manager)
    events = tmp_path / "sub-01_task-rest_events.tsv"  # never written: cannot be read

    with caplog.at_level(logging.WARNING):
        subject._sidecar_generator._generate_events_json(events, {"sub": "01", "task": "rest"}, "ieeg")

    written = json.loads(events.with_suffix(".json").read_text())
    # Default columns: "value" is described, the BIDS-predefined ones are not redefined.
    assert "value" in written and "onset" not in written
    assert _tracebacks(caplog, "subject_sidecar_generator")


def _trc_converter():
    from unittest.mock import MagicMock, patch

    from bidsificator.converters.trc_to_edf_pyeeg import TrcToEdfConverterPyEEG

    wrapper = MagicMock()
    with patch.object(TrcToEdfConverterPyEEG, "_import_platform_wrapper", return_value=wrapper):
        return TrcToEdfConverterPyEEG(), wrapper


def test_trc_that_cannot_be_opened_is_logged(tmp_path, caplog):
    converter, wrapper = _trc_converter()
    wrapper.PyIFile.side_effect = RuntimeError("synthetic: cannot open file")
    source = tmp_path / "recording.trc"
    source.write_bytes(b"0")

    with caplog.at_level(logging.WARNING):
        assert converter.can_convert(source) is False

    records = _tracebacks(caplog, "trc_to_edf_pyeeg")
    assert records and "recording.trc" in records[0].getMessage()


@pytest.mark.parametrize("method", ["_extract_hardware_filters", "_extract_reference_info"])
def test_trc_optional_metadata_failure_is_logged(method, caplog):
    from unittest.mock import MagicMock

    converter, _wrapper = _trc_converter()
    file_obj = MagicMock()
    file_obj.get_electrode_count.side_effect = RuntimeError("synthetic failure")

    with caplog.at_level(logging.WARNING):
        assert getattr(converter, method)(file_obj) is None

    assert _tracebacks(caplog, "trc_to_edf_pyeeg")


def test_same_unopenable_trc_is_logged_once(tmp_path, caplog):
    converter, wrapper = _trc_converter()
    wrapper.PyIFile.side_effect = RuntimeError("synthetic: cannot open file")
    source = tmp_path / "recording.trc"
    source.write_bytes(b"0")

    with caplog.at_level(logging.WARNING):
        for _ in range(3):
            assert converter.can_convert(source) is False

    assert len(_tracebacks(caplog, "trc_to_edf_pyeeg")) == 1


def test_systematic_check_crash_logs_one_traceback_per_run(tmp_path, monkeypatch, caplog):
    root = _ieeg_dataset(tmp_path)
    ieeg = root / "sub-01" / "ses-01" / "ieeg"
    for run in ("02", "03"):
        (ieeg / f"sub-01_ses-01_task-rest_run-{run}_ieeg.edf").write_bytes(b"0" * 64)
    monkeypatch.setattr(FileRuleValidator, "_file_matches_association_selectors", _boom)

    with caplog.at_level(logging.WARNING):
        result = ValidationService().validate_dataset(str(root))

    assert len(_internal(result.warnings)) == 3  # every file is still reported
    assert len(_tracebacks(caplog, "rules_files")) == 1  # the log is not flooded
