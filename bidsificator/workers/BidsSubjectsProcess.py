import logging
import os

from ..core.BidsFolder import BidsFolder
from ..core.logging_config import setup_logging
from .import_processor import (
    SKIPPED,
    ImportItemOutcome,
    ImportSummary,
    add_file_to_subject,
    resolve_datatype_and_suffix,
)

logger = logging.getLogger(__name__)


def check_subject_conflicts(dataset_path: str, subjects_list: list) -> list[str]:
    """
    Check for existing subjects that would conflict with the import.

    Args:
        dataset_path: Path to the BIDS dataset
        subjects_list: List of subjects to import

    Returns:
        List of subject IDs that already exist in the dataset
    """
    bids_folder = BidsFolder(dataset_path)
    subject_ids = ["sub-" + subject['subject_id'] for subject in subjects_list]
    return bids_folder.find_existing_subjects(subject_ids)


def processBidsSubjects(
    conn,
    dataset_path: str,
    subjects_list: list,
    overwrite_existing: bool = False,
    task: str = "Rest",
):
    # This runs in a separate multiprocessing.Process, so configure logging here.
    setup_logging()

    # Calculate total files across all subjects for overall progress
    total_files = sum(len(subject['files']) for subject in subjects_list)
    processed_files = 0
    summary = ImportSummary()

    def send_progress():
        # Guard against an all-empty queue (no files anywhere).
        if total_files:
            conn.send(round(100 * (float(processed_files) / total_files)))

    bids_folder = BidsFolder(dataset_path)
    for subject in subjects_list:
        try:
            # Get the subject ID and strip "sub-" if it's already there
            subject_id = subject['subject_id']
            if subject_id.lower().startswith("sub-"):
                subject_id = subject_id[4:]

            bids_subject = bids_folder.add_bids_subject(
                subject_id,  # BidsFolder expects clean ID without "sub-" prefix
                subject_description={'age': 25, 'sex': 'M'},
                overwrite=overwrite_existing
            )
        except ValueError as e:
            # add_bids_subject raises ValueError both when the subject already
            # exists (overwrite=False) and when the id is schema-invalid, so we
            # record the real cause (str(e)) rather than a hard-coded label, and
            # still advance progress past this subject's files so the bar reaches
            # 100%.
            logger.warning("Skipping subject %s: %s", subject['subject_id'], e)
            summary.items.append(ImportItemOutcome(
                path=None, subject=subject['subject_id'], status=SKIPPED, reason=str(e),
            ))
            processed_files += len(subject['files'])
            send_progress()
            continue

        # add_bids_subject never returns None (it returns the subject or raises),
        # so there is no None-check here.
        summary.subjects_created += 1

        for file in subject['files']:
            file_path = file["file_path"]

            # Skip if file does not exist (progress still emitted below).
            if not os.path.exists(file_path):
                logger.warning("File %s does not exist. Skipping.", file_path)
                summary.items.append(ImportItemOutcome(
                    path=file_path, subject=bids_subject.get_subject_id(), status=SKIPPED,
                    reason="Source file not found on disk",
                ))
                processed_files += 1
                send_progress()
                continue

            # Build entities for the file, filtering out empty values
            entities = {"sub": bids_subject.get_subject_id()}

            session_value = file.get("session", "")
            if session_value:
                # Remove "ses-" prefix if present (should be already removed by controller)
                session_clean = session_value.removeprefix("ses-")
                entities["ses"] = session_clean
                logger.debug("Session: raw='%s', clean='%s'", session_value, session_clean)

            modality = file.get("modality", "")
            logger.debug("Processing file with modality: '%s' - file: %s", modality, file_path)

            # Resolve the modality once, then reuse it for both the schema-driven
            # task-required check and the dispatch below.
            resolved = resolve_datatype_and_suffix(modality)

            # Schema decides whether this suffix requires a task entity. Unlike the
            # Import Files path, the subjects path applies one shared task value.
            if resolved is not None:
                datatype, suffix = resolved
                required_entities = bids_subject.get_required_entities_for_suffix(datatype, suffix)
                if 'task' in required_entities:
                    entities["task"] = task

            if file.get("acquisition", ""):
                entities["acq"] = file.get("acquisition")
            if file.get("reconstruction", ""):
                entities["rec"] = file.get("reconstruction")
            if file.get("contrast_agent", ""):
                entities["ce"] = file.get("contrast_agent")

            if resolved is None:
                logger.warning("Modality not recognized: %s", modality)
                summary.items.append(ImportItemOutcome(
                    path=file_path, subject=bids_subject.get_subject_id(), status=SKIPPED,
                    reason=f"Modality not recognized: '{modality}'",
                ))
            else:
                datatype, suffix = resolved
                summary.items.append(
                    add_file_to_subject(bids_subject, file_path, datatype, suffix, entities)
                )

            # Update overall progress across all subjects
            processed_files += 1
            send_progress()

    bids_folder.generate_participants_tsv()
    conn.send(summary)  # Terminal message: per-item outcomes + warnings
