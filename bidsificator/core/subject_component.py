"""Shared base for BidsSubject file-writing collaborators.

`SubjectFileWriter` and `SubjectSidecarGenerator` both do work on behalf of a
`BidsSubject`. Rather than copying the subject's state, they hold a
back-reference to the owning subject and read its live state (subject id/path,
optional metadata, contact-labeling file, and the shared schema / converter /
filename helpers) through the properties below. Reading live means a subject
rename or an optional-metadata update is always reflected, with no risk of a
stale copy.
"""

from pathlib import Path
from typing import Any


class SubjectComponent:
    """Base for collaborators that operate on a BidsSubject's behalf."""

    def __init__(self, subject):
        self._subject = subject

    @property
    def schema(self):
        return self._subject.schema

    @property
    def subject_id(self) -> str:
        return self._subject.subject_id

    @property
    def subject_path(self) -> Path:
        return self._subject.subject_path

    @property
    def dataset_path(self) -> Path:
        return self._subject.dataset_path

    @property
    def optional_metadata(self) -> dict[str, Any]:
        return self._subject.optional_metadata

    @property
    def contact_labeling_file(self) -> Path | None:
        return self._subject.contact_labeling_file

    @property
    def converter_registry(self):
        return self._subject.converter_registry

    @property
    def filename_builder(self):
        return self._subject.filename_builder

    def _format_entity(self, entity_key: str, entity_value: str) -> str:
        """Format entity with prefix (e.g., 'sub-01')."""
        return self._subject._format_entity(entity_key, entity_value)
