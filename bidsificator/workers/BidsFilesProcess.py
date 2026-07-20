import logging
import os
from pathlib import Path

from ..core.BidsFolder import BidsFolder
from ..core.logging_config import setup_logging
from .import_processor import (
    PROGRESS_DONE,
    PROGRESS_ERROR,
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

    # Attach contact labeling file if provided
    if contact_labeling_file:
        try:
            bids_subject.set_contact_labeling_file(Path(contact_labeling_file))
            logger.info("Attached contact labeling file: %s", contact_labeling_file)
        except Exception:
            logger.warning("Could not attach contact labeling file: %s", contact_labeling_file, exc_info=True)

    for index, file in enumerate(file_list):
        file_path = file["file_path"]

        # Skip if file does not exist
        if not os.path.exists(file_path):
            logger.warning("File %s does not exist. Skipping.", file_path)
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
        else:
            datatype, suffix = resolved
            add_file_to_subject(bids_subject, file_path, datatype, suffix, entities)

        progress = round(100 * (float(index + 1) / len(file_list)))
        conn.send(progress)  # Send progress to the main thread

    conn.send(PROGRESS_DONE)  # Indicate completion
