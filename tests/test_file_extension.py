"""Multi-part file extensions (``.nii.gz``) survive naming, import and crawling.

``Path.suffix`` only sees the last dot, so a ``.nii.gz`` source used to be
written as ``sub-x_T1w.gz`` with its sidecar named after the wrong stem. These
tests pin the shared helper in ``bidsificator.core.file_extension`` and the
files the writer and the crawler produce, on synthetic files only.
"""

import gzip
import json
from pathlib import Path

import pytest

from bidsificator.converters.base import FormatConverter
from bidsificator.core.BidsSubjectSchema import BidsSubject
from bidsificator.core.DataCrawler import DataCrawler
from bidsificator.core.file_extension import (
    COMPOUND_EXTENSIONS,
    get_extension,
    get_stem,
    replace_extension,
    split_extension,
)

# --------------------------------------------------------------------------- #
# helper
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "name, stem, extension",
    [
        ("sub-01_T1w.nii.gz", "sub-01_T1w", ".nii.gz"),
        ("sub-01_T1w.nii", "sub-01_T1w", ".nii"),
        ("sub-01_task-rest_ieeg.edf", "sub-01_task-rest_ieeg", ".edf"),
        ("sub-01_T1w.json", "sub-01_T1w", ".json"),
        ("scan.v2.NII.GZ", "scan.v2", ".NII.GZ"),  # case kept as written
        ("sub-01_physio.tsv.gz", "sub-01_physio", ".tsv.gz"),
        ("archive.gz", "archive", ".gz"),  # a lone .gz is not a compound extension
        ("README", "README", ""),
        (".nii.gz", ".nii", ".gz"),  # no stem left: falls back to the last dot
    ],
)
def test_split_extension(name, stem, extension):
    assert split_extension(name) == (stem, extension)
    assert get_stem(name) == stem
    assert get_extension(name) == extension


def test_split_extension_uses_the_file_name_only():
    assert split_extension(Path("/data/v1.2/sub-01_T1w.nii.gz")) == ("sub-01_T1w", ".nii.gz")


def test_replace_extension_replaces_the_whole_extension():
    data = Path("/ds/sub-01/anat/sub-01_T1w.nii.gz")
    assert replace_extension(data, ".json") == Path("/ds/sub-01/anat/sub-01_T1w.json")
    assert replace_extension(Path("sub-01_ieeg.edf"), ".json") == Path("sub-01_ieeg.json")


def test_every_multi_part_schema_extension_is_known(schema_manager):
    # The helper's list is hand-written; the schema is the reference.
    extensions = schema_manager._raw_schema["objects"]["extensions"]
    multi_part = {
        entry["value"].rstrip("/") for entry in extensions.values() if entry["value"].count(".") > 1
    }
    assert ".nii.gz" in multi_part
    assert multi_part <= set(COMPOUND_EXTENSIONS)


# --------------------------------------------------------------------------- #
# writer: what lands on disk
# --------------------------------------------------------------------------- #

def _synthetic_nii_gz(path: Path) -> Path:
    """A gzip file with a few zero bytes; the writer copies it without reading it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as handle:
        handle.write(bytes(64))
    return path


def _files_under(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def test_nii_gz_source_keeps_its_extension_and_sidecar_name(schema_manager, tmp_path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    source = _synthetic_nii_gz(tmp_path / "inputs" / "scan.nii.gz")
    subject = BidsSubject("01", dataset, schema_manager)

    result = subject.add_file(source, "anat", suffix="T1w")

    assert result["target_path"].name == "sub-01_T1w.nii.gz"
    assert _files_under(dataset / "sub-01") == ["anat/sub-01_T1w.json", "anat/sub-01_T1w.nii.gz"]
    assert (dataset / "sub-01" / "anat" / "sub-01_T1w.nii.gz").read_bytes() == source.read_bytes()
    assert isinstance(json.loads((dataset / "sub-01" / "anat" / "sub-01_T1w.json").read_text()), dict)


class _FakeNiftiConverter(FormatConverter):
    """Stands in for the DICOM converter (an external tool): writes a .nii.gz."""

    source_extensions = [".fakescan"]
    target_format = "nifti"

    def can_convert(self, source_path: Path) -> bool:
        return True

    def convert(self, source_path: Path, output_dir: Path = None) -> Path:
        return _synthetic_nii_gz(output_dir / "converted_series.nii.gz")


def test_converted_nii_gz_keeps_its_extension(schema_manager, tmp_path):
    # The conversion path (DICOM in the app) names its output from the
    # converted file's extension, which is '.nii.gz' for dicom2nifti.
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    source = tmp_path / "inputs" / "series.fakescan"
    source.parent.mkdir()
    source.write_bytes(b"synthetic")
    subject = BidsSubject("01", dataset, schema_manager)
    subject.converter_registry.register(_FakeNiftiConverter())

    result = subject.add_file(source, "anat", suffix="T1w")

    assert result["target_path"].name == "sub-01_T1w.nii.gz"
    assert _files_under(dataset / "sub-01") == ["anat/sub-01_T1w.json", "anat/sub-01_T1w.nii.gz"]


# --------------------------------------------------------------------------- #
# crawler: a configured '.nii.gz' extension finds the file
# --------------------------------------------------------------------------- #

def test_crawler_finds_files_by_multi_part_extension(tmp_path):
    scan_dir = tmp_path / "source" / "PAT001" / "mri"
    _synthetic_nii_gz(scan_dir / "T1.nii.gz")
    (scan_dir / "notes.gz").write_bytes(b"x")  # must not match '.nii.gz'
    (scan_dir / "T1.NII").write_bytes(b"x")  # case-insensitive match on '.nii'
    config = tmp_path / "config.yaml"
    config.write_text(
        "data_paths:\n"
        f'  main: "{tmp_path / "source"}"\n'
        'subject_pattern: "PAT*"\n'
        "file_types:\n"
        "  mri_pre:\n"
        '    description: "Pre-surgery T1-weighted MRI"\n'
        '    folder: "mri"\n'
        '    extensions: [".nii", ".nii.gz"]\n'
    )

    subjects = DataCrawler(str(config)).process_subject_data()

    assert len(subjects) == 1
    found = sorted(Path(p).name for p in subjects[0]["data"]["mri_pre"]["file_paths"])
    assert found == ["T1.NII", "T1.nii.gz"]
