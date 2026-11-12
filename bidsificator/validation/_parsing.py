"""Shared BIDS-filename parsing helpers used by both rule modules.

These were duplicated inside ValidationService (`_parse_filename`,
`_extract_suffix_from_filename`, `_parse_entities_from_filename`); pulled out
here so the file-rules and metadata-rules modules share one implementation.
"""

from pathlib import Path

from bidsificator.core.file_extension import get_stem


def parse_filename(filename: str) -> tuple[dict[str, str], str | None]:
    """Parse a BIDS filename (no extension) into (entities, suffix)."""
    entities: dict[str, str] = {}
    suffix: str | None = None

    # Split on underscores
    parts = filename.split('_')

    for i, part in enumerate(parts):
        if '-' in part:
            key, value = part.split('-', 1)
            entities[key] = value
        elif i == len(parts) - 1:
            # Last part without dash is the suffix
            suffix = part

    return entities, suffix


def extract_suffix_from_filename(filename: str) -> str:
    """Extract the suffix (last part before extension) from a filename."""
    name = get_stem(filename)  # whole extension removed ('.nii.gz')
    parts = name.split('_')
    return parts[-1] if parts else ""


def parse_entities_from_filename(file_path: Path) -> dict[str, str]:
    """Parse BIDS entities from a file path's name (excludes the suffix)."""
    filename = get_stem(file_path)  # Remove extension ('.nii.gz' as a whole)
    entities: dict[str, str] = {}

    parts = filename.split('_')
    for part in parts[:-1]:  # Skip last part (suffix)
        if '-' in part:
            key, value = part.split('-', 1)
            entities[key] = value

    return entities
