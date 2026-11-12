"""File-name extension helpers that keep multi-part extensions whole.

``Path.suffix``, ``Path.stem`` and ``Path.with_suffix`` only know the last dot:
for ``sub-01_T1w.nii.gz`` they give ``.gz``, ``sub-01_T1w.nii`` and
``sub-01_T1w.nii.json``. Code that names or pairs BIDS files uses the helpers
below instead, so ``.nii.gz`` and the other multi-part extensions stay in one piece.
"""

from pathlib import Path

# Multi-part extensions of BIDS data files, lower case. Every extension of the
# BIDS schema with more than one dot is listed here (asserted by
# tests/test_file_extension.py), plus '.ome.tiff', which the file registry accepts.
COMPOUND_EXTENSIONS = (
    '.nii.gz',
    '.tsv.gz',
    '.dlabel.nii',
    '.label.gii',
    '.ome.btf',
    '.ome.tif',
    '.ome.tiff',
    '.ome.zarr',
)


def split_extension(file_name: str | Path) -> tuple[str, str]:
    """
    Split a file name into ``(stem, extension)``, keeping a multi-part extension whole.

    The extension is returned as written (case preserved) and includes its
    leading dot; it is ``''`` when the name has none. Only the final path
    component is looked at.

    Example:
        >>> split_extension('sub-01_T1w.nii.gz')
        ('sub-01_T1w', '.nii.gz')
        >>> split_extension('sub-01_task-rest_ieeg.edf')
        ('sub-01_task-rest_ieeg', '.edf')
    """
    name = Path(file_name).name
    lowered = name.lower()
    for compound in COMPOUND_EXTENSIONS:
        if lowered.endswith(compound) and len(name) > len(compound):
            return name[:-len(compound)], name[-len(compound):]

    path = Path(name)
    return path.stem, path.suffix


def get_extension(file_name: str | Path) -> str:
    """Extension of a file name, multi-part extensions kept whole (``'.nii.gz'``)."""
    return split_extension(file_name)[1]


def get_stem(file_name: str | Path) -> str:
    """File name without its extension, multi-part extensions removed whole."""
    return split_extension(file_name)[0]


def replace_extension(file_path: Path, new_extension: str) -> Path:
    """Path of ``file_path`` with its whole extension replaced by ``new_extension``."""
    file_path = Path(file_path)
    return file_path.with_name(get_stem(file_path) + new_extension)
