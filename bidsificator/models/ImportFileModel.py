"""Model for managing individual import file data and operations."""

import os
from dataclasses import dataclass
from typing import Any


class _Mixed:
    """Sentinel returned by ``common_value_for`` when the selected files disagree.

    A distinct object (not ``None``/``""``) so it can never collide with a real
    field value such as an empty session or a free-typed session name. The
    ``(multiple values)`` *display* string is the view's concern, not the model's.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return "<MIXED>"


#: Sentinel: the batch-selected files hold differing values for a field.
MIXED = _Mixed()


@dataclass
class ImportFileData:
    """Data structure for a single import file."""
    file_name: str
    file_path: str
    modality: str
    task: str = ""
    session: str = ""
    contrast_agent: str = ""
    acquisition: str = ""
    reconstruction: str = ""
    intended_subject: str = ""

    def __post_init__(self):
        """Validate and clean data after initialization."""
        # Ensure file_name matches file_path
        if self.file_path and not self.file_name:
            self.file_name = os.path.basename(self.file_path)

        # Clean session prefix if present
        if self.session.startswith("ses-"):
            self.session = self.session[4:]

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary format (for backward compatibility)."""
        return {
            "file_name": self.file_name,
            "file_path": self.file_path,
            "modality": self.modality,
            "task": self.task,
            "session": self.session,
            "contrast_agent": self.contrast_agent,
            "acquisition": self.acquisition,
            "reconstruction": self.reconstruction,
            "intended_subject": self.intended_subject
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ImportFileData':
        """Create from dictionary format (for backward compatibility)."""
        return cls(
            file_name=data.get("file_name", ""),
            file_path=data.get("file_path", ""),
            modality=data.get("modality", ""),
            task=data.get("task", ""),
            session=data.get("session", ""),
            contrast_agent=data.get("contrast_agent", ""),
            acquisition=data.get("acquisition", ""),
            reconstruction=data.get("reconstruction", ""),
            intended_subject=data.get("intended_subject", "")
        )

    def validate(self) -> tuple[bool, str]:
        """Validate the file data."""
        if not self.file_name:
            return False, "File name is required"
        if not self.file_path:
            return False, "File path is required"
        if not self.modality:
            return False, "Modality is required"
        if not os.path.exists(self.file_path):
            return False, f"File does not exist: {self.file_path}"
        return True, ""

    def get_session_with_prefix(self) -> str:
        """Get session with 'ses-' prefix if session exists."""
        return f"ses-{self.session}" if self.session else ""


class ImportFileModel:
    """Model for managing import file data and operations."""

    def __init__(self):
        """Initialize empty import file model."""
        self._files: list[ImportFileData] = []
        self._current_subject: str = ""

    @property
    def files(self) -> list[ImportFileData]:
        """Get list of import files."""
        return self._files.copy()

    @property
    def current_subject(self) -> str:
        """Get current subject ID."""
        return self._current_subject

    @current_subject.setter
    def current_subject(self, subject_id: str):
        """Set current subject ID."""
        self._current_subject = subject_id

    def add_file(self, file_data: ImportFileData) -> bool:
        """
        Add a file to the import list.

        Args:
            file_data: ImportFileData instance to add

        Returns:
            True if added successfully, False if duplicate
        """
        # Check for duplicates
        if self.has_file(file_data.file_path):
            return False

        # Set intended subject if not already set
        if not file_data.intended_subject:
            file_data.intended_subject = self._current_subject

        self._files.append(file_data)
        return True

    def remove_file(self, index: int) -> bool:
        """
        Remove a file by index.

        Args:
            index: Index of file to remove

        Returns:
            True if removed successfully, False if index invalid
        """
        if 0 <= index < len(self._files):
            self._files.pop(index)
            return True
        return False

    def remove_file_by_path(self, file_path: str) -> bool:
        """
        Remove a file by path.

        Args:
            file_path: Path of file to remove

        Returns:
            True if removed successfully, False if not found
        """
        for i, file_data in enumerate(self._files):
            if file_data.file_path == file_path:
                self._files.pop(i)
                return True
        return False

    def has_file(self, file_path: str) -> bool:
        """
        Check if a file path already exists in the list.

        Args:
            file_path: Path to check

        Returns:
            True if file exists, False otherwise
        """
        return any(file_data.file_path == file_path for file_data in self._files)

    def get_file(self, index: int) -> ImportFileData | None:
        """
        Get file data by index.

        Args:
            index: Index of file to get

        Returns:
            ImportFileData instance or None if index invalid
        """
        if 0 <= index < len(self._files):
            return self._files[index]
        return None

    def update_file(self, index: int, file_data: ImportFileData) -> bool:
        """
        Update file data at index.

        Args:
            index: Index of file to update
            file_data: New file data

        Returns:
            True if updated successfully, False if index invalid
        """
        if 0 <= index < len(self._files):
            self._files[index] = file_data
            return True
        return False

    def update_all_subjects(self, new_subject: str):
        """
        Update all files to use a new subject ID.

        Args:
            new_subject: New subject ID to apply to all files
        """
        self._current_subject = new_subject
        for file_data in self._files:
            file_data.intended_subject = new_subject

    def update_files_fields(self, indices: list[int], fields: dict[str, str]) -> list[int]:
        """Apply only the given field keys to the files at ``indices`` (batch edit).

        ``fields`` maps :class:`ImportFileData` attribute names to new values;
        keys absent from ``fields`` are left untouched on each file, so setting
        the modality of ten files does not wipe their individual tasks. Unknown
        keys are ignored. The session value has any ``ses-`` prefix stripped
        (stored bare), matching the single-file path in ``ImportSessionModel``.

        Args:
            indices: File indices to update (invalid indices skipped).
            fields: Attribute-name -> new value.

        Returns:
            The indices actually updated (valid + at least attempted).
        """
        updated: list[int] = []
        for index in indices:
            file_data = self.get_file(index)
            if file_data is None:
                continue
            for key, value in fields.items():
                if not hasattr(file_data, key):
                    continue
                if key == "session" and isinstance(value, str) and value.startswith("ses-"):
                    value = value[4:]
                setattr(file_data, key, value)
            updated.append(index)
        return updated

    def common_value_for(self, indices: list[int], field: str) -> Any:
        """Return the value all files at ``indices`` share for ``field``, else ``MIXED``.

        Used to render the batch form: a shared value is shown directly; ``MIXED``
        tells the view to show a "(multiple values)" placeholder. Session is
        returned bare (no ``ses-`` prefix); the view prefixes it for display.

        Args:
            indices: File indices to compare.
            field: :class:`ImportFileData` attribute name.

        Returns:
            The shared value, or :data:`MIXED` when the files disagree (or none
            are valid).
        """
        values = set()
        for index in indices:
            file_data = self.get_file(index)
            if file_data is None or not hasattr(file_data, field):
                continue
            values.add(getattr(file_data, field))
        if len(values) == 1:
            return values.pop()
        return MIXED

    def reassign_acquisitions(self, indices: list[int]) -> None:
        """Recompute acquisition numbers for the files at ``indices`` only.

        Each listed file is treated as freshly (re)added to its current
        ``(session, modality, task)`` group: its acquisition is blanked, then set
        to the next free number in that group computed against *every other file*
        via :meth:`ImportService.get_next_acquisition_number` (the same helper the
        add path uses). Files **not** listed keep their acquisition unchanged, so a
        batch edit never renumbers files the user did not touch.

        All listed files are blanked *before* any are assigned, so several files
        moved into the same group get clean sequential numbers (``01, 02, …``)
        rather than continuing past their stale values.

        Args:
            indices: File indices whose acquisition should be recomputed
                (typically the edited files whose group key changed).
        """
        # Local import mirrors ImportSessionModel.add_files; avoids a module-load
        # cycle (ImportService consumes file dicts, not this model).
        from ..services.ImportService import ImportService

        ordered = sorted({i for i in indices if self.get_file(i) is not None})
        if not ordered:
            return

        # Blank first so co-moved files don't inflate each other's group max.
        for index in ordered:
            self._files[index].acquisition = ""

        # Then assign in list order; each file sees only committed numbers
        # (earlier reassigned files + untouched files), never a stale one.
        for index in ordered:
            file_data = self._files[index]
            others = [f.to_dict() for j, f in enumerate(self._files) if j != index]
            file_data.acquisition = ImportService.get_next_acquisition_number(
                others, file_data.session, file_data.modality, file_data.task
            )

    def preview_acquisition(self, index: int, session: str, modality: str, task: str) -> str:
        """The acquisition file ``index`` would get in group ``(session, modality, task)``.

        Read-only (nothing is mutated) — used to keep the single-file form's
        Acquisition field live as the user changes the group dropdowns. When the
        target group matches the file's current group the file's own acquisition is
        returned (so a value already shown / manually entered is left alone); when
        it differs, the next free number in the target group is returned, computed
        against the other files exactly as the save-time reassignment does.

        Args:
            index: File whose acquisition to preview.
            session: Target session (a leading ``ses-`` is stripped).
            modality: Target display modality.
            task: Target task.

        Returns:
            The acquisition string, or ``""`` if the index is invalid.
        """
        file_data = self.get_file(index)
        if file_data is None:
            return ""
        if session.startswith("ses-"):
            session = session[4:]
        if (session, modality, task) == (file_data.session, file_data.modality, file_data.task):
            return file_data.acquisition

        from ..services.ImportService import ImportService

        others = [f.to_dict() for j, f in enumerate(self._files) if j != index]
        return ImportService.get_next_acquisition_number(others, session, modality, task)

    def clear(self):
        """Clear all files from the model."""
        self._files.clear()
        self._current_subject = ""

    def count(self) -> int:
        """Get number of files in the model."""
        return len(self._files)

    def is_empty(self) -> bool:
        """Check if the model is empty."""
        return len(self._files) == 0

    def get_files_as_dicts(self) -> list[dict[str, str]]:
        """
        Get files as list of dictionaries (for backward compatibility).

        Returns:
            List of file dictionaries
        """
        return [file_data.to_dict() for file_data in self._files]

    def load_from_dicts(self, files_data: list[dict[str, Any]], subject_id: str = ""):
        """
        Load files from list of dictionaries (for backward compatibility).

        Args:
            files_data: List of file dictionaries
            subject_id: Subject ID to set
        """
        self.clear()
        self._current_subject = subject_id

        for file_dict in files_data:
            file_data = ImportFileData.from_dict(file_dict)
            if not file_data.intended_subject:
                file_data.intended_subject = subject_id
            self._files.append(file_data)

    def validate_all(self) -> tuple[bool, list[str]]:
        """
        Validate all files in the model.

        Returns:
            Tuple of (all_valid, error_messages)
        """
        all_valid = True
        errors = []

        for i, file_data in enumerate(self._files):
            is_valid, error = file_data.validate()
            if not is_valid:
                all_valid = False
                errors.append(f"File {i+1}: {error}")

        return all_valid, errors

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the files.

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_files": len(self._files),
            "modalities": {},
            "sessions": set(),
            "tasks": set(),
            "subjects": set()
        }

        for file_data in self._files:
            # Count modalities
            modality = file_data.modality
            stats["modalities"][modality] = stats["modalities"].get(modality, 0) + 1

            # Collect unique values
            if file_data.session:
                stats["sessions"].add(file_data.session)
            if file_data.task:
                stats["tasks"].add(file_data.task)
            if file_data.intended_subject:
                stats["subjects"].add(file_data.intended_subject)

        # Convert sets to lists for JSON serialization
        stats["sessions"] = list(stats["sessions"])
        stats["tasks"] = list(stats["tasks"])
        stats["subjects"] = list(stats["subjects"])

        return stats
