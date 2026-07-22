"""Shared logic for the file/subject import worker processes.

Both :func:`processBidsFiles` and :func:`processBidsSubjects` run in a separate
``multiprocessing.Process`` and place source files into a ``BidsSubject`` using
the same modality-dispatch rules. That dispatch used to be copy-pasted across
the two processors (and duplicated a second time inside the subjects processor);
it now lives here so the two paths can no longer drift.

This module also owns the protocol exchanged over the ``mp.Pipe``. Ordinary
values are 0-100 progress percentages; :data:`PROGRESS_ERROR` marks a hard abort;
and the terminal success message is an :class:`ImportSummary` carrying a
per-item outcome list (see :func:`classify_message`, which the QThread readers
use to discriminate message *type* before any ordering comparison). The bare
:data:`PROGRESS_DONE` sentinel is superseded by the summary but still recognized
for backward compatibility.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

PROGRESS_DONE = 101   # legacy bare completion sentinel (superseded by ImportSummary)
PROGRESS_ERROR = -1   # processor hit an unrecoverable error and bailed out

# Per-item outcome statuses.
IMPORTED = "imported"   # placed on disk successfully
FAILED = "failed"       # add_file / conversion raised
SKIPPED = "skipped"     # source missing, modality unrecognized, or subject skipped

# Import modality display names that map to the BIDS ``anat`` datatype. The
# suffix is the text before " (anat)" (e.g. "T1w (anat)" -> "T1w"). Defined once
# here and imported by both QThread workers instead of being repeated in each.
ANATOMICAL_MODALITIES: frozenset[str] = frozenset({
    "T1w (anat)", "T2w (anat)", "T1rho (anat)",
    "T2* (anat)", "FLAIR (anat)", "CT (anat)",
})


@dataclass
class ImportItemOutcome:
    """Outcome of a single queued item: one source file, or a skipped subject.

    Instances cross the ``mp.Pipe`` inside an :class:`ImportSummary`, so every
    field is a picklable primitive (safe under the macOS ``spawn`` start method).
    ``path`` is ``None`` for a subject-level outcome (a subject that could not be
    created); ``reason`` is a human-readable cause for ``FAILED``/``SKIPPED`` and
    ``None`` for ``IMPORTED``.
    """

    path: str | None
    subject: str | None
    status: str
    reason: str | None = None


@dataclass
class ImportSummary:
    """Structured terminal result a worker sends in place of ``PROGRESS_DONE``.

    Carries the per-item outcomes, summary-level warnings (failures that are not
    tied to one queued item, e.g. a contact-labeling file failing to attach), and
    the number of subjects created (batch import only; 0 for single-file import).
    Counts are derived from ``items`` so they can never disagree with the list.
    """

    items: list[ImportItemOutcome] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    subjects_created: int = 0

    @property
    def imported(self) -> int:
        return sum(1 for item in self.items if item.status == IMPORTED)

    @property
    def failed(self) -> int:
        return sum(1 for item in self.items if item.status == FAILED)

    @property
    def skipped(self) -> int:
        return sum(1 for item in self.items if item.status == SKIPPED)

    @property
    def total(self) -> int:
        return len(self.items)


class MessageKind(Enum):
    """Classification of a message received over the worker pipe."""

    PROGRESS = "progress"   # int 0-100 progress percentage
    DONE = "done"           # legacy bare PROGRESS_DONE completion sentinel
    SUMMARY = "summary"     # terminal ImportSummary payload
    ERROR = "error"         # PROGRESS_ERROR hard-abort sentinel
    UNKNOWN = "unknown"     # anything else -> a protocol error, never a hang


def classify_message(message) -> MessageKind:
    """Classify a pipe message by *type* before any ordering comparison.

    The readers must branch on this rather than doing ``message <= PROGRESS_ERROR``
    directly: a non-int terminal message would otherwise raise ``TypeError`` inside
    ``run()`` and emit neither ``finished`` nor ``error``, hanging the UI. An
    unrecognized message is surfaced as :attr:`MessageKind.UNKNOWN` (a protocol
    error) instead.
    """
    if isinstance(message, ImportSummary):
        return MessageKind.SUMMARY
    # bool is an int subclass; never let True/False masquerade as progress.
    if isinstance(message, bool):
        return MessageKind.UNKNOWN
    if isinstance(message, int):
        if message == PROGRESS_DONE:
            return MessageKind.DONE
        if message <= PROGRESS_ERROR:
            return MessageKind.ERROR
        if 0 <= message <= 100:
            return MessageKind.PROGRESS
        return MessageKind.UNKNOWN
    return MessageKind.UNKNOWN


def resolve_datatype_and_suffix(modality: str) -> tuple[str, str] | None:
    """Map an import modality display name to a ``(datatype, suffix)`` pair.

    Returns ``None`` for an unrecognized modality so callers can log and skip.
    """
    if modality == "ieeg (ieeg)":
        return "ieeg", "ieeg"
    if modality == "eeg (eeg)":
        return "eeg", "eeg"
    if modality == "photo (ieeg)":
        return "ieeg", "photo"
    if modality in ANATOMICAL_MODALITIES:
        return "anat", modality.split("(")[0].strip()  # "T1w (anat)" -> "T1w"
    return None


def add_file_to_subject(bids_subject, file_path: str, datatype: str, suffix: str, entities: dict) -> ImportItemOutcome:
    """Add one source file to ``bids_subject`` and return its outcome.

    Conversions (including DICOM) are handled inside ``BidsSubject.add_file()``. A
    failure is logged and returned as a ``FAILED`` outcome carrying the exception
    text, so a single bad file does not abort the rest of the batch. The reason is
    the real exception text (``str(e)``), not a branch-inferred label.
    """
    subject_id = bids_subject.get_subject_id()
    try:
        result = bids_subject.add_file(
            source_path=file_path,
            datatype=datatype,
            entities=entities,
            suffix=suffix,
        )
        logger.info("Added %s file: %s", suffix, result.get("target_path", file_path))
        return ImportItemOutcome(path=file_path, subject=subject_id, status=IMPORTED)
    except Exception as e:
        logger.exception("Error processing file %s; recording as failed", file_path)
        return ImportItemOutcome(path=file_path, subject=subject_id, status=FAILED, reason=str(e))
