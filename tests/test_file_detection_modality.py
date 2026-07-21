"""Pin the display-modality that the Import Files add path assigns per file type.

After PR 8a, adding files on the Import Files tab goes through
ImportService.process_multiple_files (schema-driven FileDetectionService), not a
duplicate detector in the view. These tests document what that path actually
produces for the formats this tool handles — in particular that BrainVision
(.vhdr/.bdf) is accepted as ``ieeg (ieeg)`` (the registry classifies it as iEEG),
not rejected. Detection is filename/extension based, so empty temp files suffice.
"""

import tempfile
from pathlib import Path

import pytest

from bidsificator.services.ImportService import ImportService

_DEFAULTS = {"task": "rest", "session": "", "contrast_agent": "", "reconstruction": ""}


def _add_one(filename: str):
    """Run a single file through the add path; return (successful, failed)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / filename
        p.write_bytes(b"")  # detection is name/extension based; content not needed
        return ImportService.process_multiple_files([str(p)], _DEFAULTS, [])


@pytest.mark.parametrize("filename", ["rec.trc", "rec.edf", "rec.vhdr", "rec.bdf"])
def test_ephys_formats_are_accepted_as_ieeg(filename):
    successful, failed = _add_one(filename)
    assert not failed, f"{filename} unexpectedly rejected: {failed}"
    assert len(successful) == 1
    assert successful[0]["modality"] == "ieeg (ieeg)"


def test_anatomical_nifti_is_accepted_as_t1w():
    successful, failed = _add_one("scan_t1w.nii")
    assert not failed
    assert len(successful) == 1
    assert successful[0]["modality"] == "T1w (anat)"
