import logging
import os
from pathlib import Path

from ..core.BidsFolder import BidsFolder
from ..core.logging_config import setup_logging
from .protocol import PROGRESS_DONE, PROGRESS_ERROR

logger = logging.getLogger(__name__)


def processBidsFiles(
    conn,
    dataset_path: str,
    subject_name: str,
    file_list: list,
    anatomical_modalities: set[str],
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

        # Define entities for the file
        # Build entities dict, filtering out empty values
        entities = {}
        entities["sub"] = bids_subject.get_subject_id()

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

        # Process file based on its modality
        modality = file.get("modality", "")
        if modality == "ieeg (ieeg)":
            try:
                # Map modality to datatype for schema-driven BidsSubject
                result = bids_subject.add_file(
                    source_path=file_path,
                    datatype='ieeg',
                    entities=entities,
                    suffix='ieeg'
                )
                logger.info("Added iEEG file: %s", result.get('target_path', file_path))
            except Exception:
                logger.exception("Error processing file %s; skipping", file_path)
        elif modality == "eeg (eeg)":
            try:
                # Map modality to datatype for schema-driven BidsSubject
                result = bids_subject.add_file(
                    source_path=file_path,
                    datatype='eeg',
                    entities=entities,
                    suffix='eeg'
                )
                logger.info("Added EEG file: %s", result.get('target_path', file_path))
            except Exception:
                logger.exception("Error processing file %s; skipping", file_path)
        elif modality == "photo (ieeg)":
            try:
                # Photos are stored in ieeg datatype with photo suffix
                result = bids_subject.add_file(
                    source_path=file_path,
                    datatype='ieeg',
                    entities=entities,
                    suffix='photo'
                )
                logger.info("Added photo file: %s", result.get('target_path', file_path))
            except Exception:
                logger.exception("Error processing photo file %s; skipping", file_path)
        elif modality in anatomical_modalities:
            try:
                # Let BidsSubject.add_file() handle ALL conversions (including DICOM)
                # Map modality display name to suffix
                suffix = str(modality).replace(" (anat)", "")
                result = bids_subject.add_file(
                    source_path=file_path,
                    datatype='anat',
                    entities=entities,
                    suffix=suffix
                )
                logger.info("Added anatomical file: %s", result.get('target_path', file_path))
            except Exception:
                logger.exception("Error processing anatomical file %s; skipping", file_path)
        else:
            logger.warning("Modality not recognized: %s", modality)

        progress = round(100 * (float(index + 1) / len(file_list)))
        conn.send(progress)  # Send progress to the main thread

    conn.send(PROGRESS_DONE)  # Indicate completion
