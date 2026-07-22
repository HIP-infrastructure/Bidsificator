import logging
import os
from pathlib import Path

from ..core.BidsFolder import BidsFolder
from ..core.logging_config import setup_logging
from .import_processor import (
    PROGRESS_ERROR,
    SKIPPED,
    ImportItemOutcome,
    ImportSummary,
    add_file_to_subject,
    resolve_datatype_and_suffix,
)

logger = logging.getLogger(__name__)


def processBidsFiles(
    conn,
    dataset_path: str,
    subject_name: str,
    file_list: list,
    contact_labeling_file: str = None,
):
    # This runs in a separate multiprocessing.Process, so configure logging here.
    setup_logging()

    bids_folder = BidsFolder(dataset_path)
    bids_subject = bids_folder.get_bids_subject(subject_name)

    if bids_subject is None:
        logger.error("Subject '%s' not found in dataset '%s'", subject_name, dataset_path)
        conn.send(PROGRESS_ERROR)
        return

    summary = ImportSummary()
    subject_id = bids_subject.get_subject_id()

    # Attach contact labeling file if provided. A failure here is not tied to any
    # one queued file, so it surfaces as a summary-level warning, not a per-item
    # outcome.
    if contact_labeling_file:
        try:
            bids_subject.set_contact_labeling_file(Path(contact_labeling_file))
            logger.info("Attached contact labeling file: %s", contact_labeling_file)
        except Exception as e:
            logger.warning("Could not attach contact labeling file: %s", contact_labeling_file, exc_info=True)
            summary.warnings.append(
                f"Could not attach contact labeling file '{contact_labeling_file}': {e}"
            )

    total = len(file_list)
    for index, file in enumerate(file_list):
        file_path = file["file_path"]

        # A missing source file is skipped, but its progress is still emitted so
        # the bar reaches 100% (previously the `continue` jumped past the send).
        if not os.path.exists(file_path):
            logger.warning("File %s does not exist. Skipping.", file_path)
            summary.items.append(ImportItemOutcome(
                path=file_path, subject=subject_id, status=SKIPPED,
                reason="Source file not found on disk",
            ))
            conn.send(round(100 * (float(index + 1) / total)))
            continue

        # Build entities dict, filtering out empty values
        entities = {"sub": bids_subject.get_subject_id()}
        if file.get("session", ""):
            entities["ses"] = file.get("session")
        if file.get("task", ""):
            entities["task"] = file.get("task")
        if file.get("acquisition", ""):
            entities["acq"] = file.get("acquisition")
        if file.get("reconstruction", ""):
            entities["rec"] = file.get("reconstruction")
        if file.get("contrast_agent", ""):
            entities["ce"] = file.get("contrast_agent")

        # Dispatch on modality via the shared resolver
        modality = file.get("modality", "")
        resolved = resolve_datatype_and_suffix(modality)
        if resolved is None:
            logger.warning("Modality not recognized: %s", modality)
            summary.items.append(ImportItemOutcome(
                path=file_path, subject=subject_id, status=SKIPPED,
                reason=f"Modality not recognized: '{modality}'",
            ))
        else:
            datatype, suffix = resolved
            summary.items.append(
                add_file_to_subject(bids_subject, file_path, datatype, suffix, entities)
            )

        progress = round(100 * (float(index + 1) / total))
        conn.send(progress)  # Send progress to the main thread

    conn.send(summary)  # Terminal message: per-item outcomes + warnings
