"""Shared logic for the file/subject import worker processes.

Both :func:`processBidsFiles` and :func:`processBidsSubjects` run in a separate
``multiprocessing.Process`` and place source files into a ``BidsSubject`` using
the same modality-dispatch rules. That dispatch used to be copy-pasted across
the two processors (and duplicated a second time inside the subjects processor);
it now lives here so the two paths can no longer drift.

This module also owns the progress sentinels exchanged over the ``mp.Pipe``:
ordinary values are 0–100 progress percentages, and the two constants below name
the values that are not.
"""

import logging

logger = logging.getLogger(__name__)

PROGRESS_DONE = 101   # processor finished successfully
PROGRESS_ERROR = -1   # processor hit an unrecoverable error and bailed out

# Import modality display names that map to the BIDS ``anat`` datatype. The
# suffix is the text before " (anat)" (e.g. "T1w (anat)" -> "T1w"). Defined once
# here and imported by both QThread workers instead of being re-declared in each.
ANATOMICAL_MODALITIES: frozenset[str] = frozenset({
    "T1w (anat)", "T2w (anat)", "T1rho (anat)",
    "T2* (anat)", "FLAIR (anat)", "CT (anat)",
})


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


def add_file_to_subject(bids_subject, file_path: str, datatype: str, suffix: str, entities: dict) -> None:
    """Add one source file to ``bids_subject``, logging success or failure.

    Conversions (including DICOM) are handled inside ``BidsSubject.add_file()``.
    Exceptions are logged and swallowed so a single bad file does not abort the
    rest of the batch.
    """
    try:
        result = bids_subject.add_file(
            source_path=file_path,
            datatype=datatype,
            entities=entities,
            suffix=suffix,
        )
        logger.info("Added %s file: %s", suffix, result.get("target_path", file_path))
    except Exception:
        logger.exception("Error processing file %s; skipping", file_path)
