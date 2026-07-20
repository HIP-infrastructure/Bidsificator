import os
import logging

from ..core.BidsFolder import BidsFolder
from ..core.logging_config import setup_logging
from .protocol import PROGRESS_DONE, PROGRESS_ERROR

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
    anatomical_modalities: set[str],
    overwrite_existing: bool = False,
    task: str = "Rest",
):
    # This runs in a separate multiprocessing.Process, so configure logging here.
    setup_logging()

    # Calculate total files across all subjects for overall progress
    total_files = sum(len(subject['files']) for subject in subjects_list)
    processed_files = 0


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
            # Subject already exists and overwrite=False
            logger.warning("Skipping subject %s: %s", subject['subject_id'], e)
            continue

        if bids_subject is None:
            logger.error("Failed to create subject %s in dataset %s", subject['subject_id'], dataset_path)
            conn.send(PROGRESS_ERROR)
            return

        for index, file in enumerate(subject['files']):
            file_path = file["file_path"]

            # Skip if file does not exist
            if not os.path.exists(file_path):
                logger.warning("File %s does not exist. Skipping.", file_path)
                continue

            # Define entities for the file, filtering out empty values
            entities = {}
            entities["sub"] = bids_subject.get_subject_id()

            session_value = file.get("session", "")
            if session_value:
                # Remove "ses-" prefix if present (should be already removed by controller)
                session_clean = session_value.removeprefix("ses-")
                entities["ses"] = session_clean
                logger.debug("Session: raw='%s', clean='%s'", session_value, session_clean)

            # Process file based on its modality - use existing hardcoded approach for consistency
            modality = file.get("modality", "")
            logger.debug("Processing file with modality: '%s' - file: %s", modality, file_path)

            # Use schema to determine if task is required for specific modality types
            # This is the schema-driven improvement while keeping existing patterns
            if modality == "ieeg (ieeg)":
                required_entities = bids_subject.get_required_entities_for_suffix('ieeg', 'ieeg')
                if 'task' in required_entities:
                    entities["task"] = task
            elif modality == "eeg (eeg)":
                required_entities = bids_subject.get_required_entities_for_suffix('eeg', 'eeg')
                if 'task' in required_entities:
                    entities["task"] = task
            elif modality == "photo (ieeg)":
                required_entities = bids_subject.get_required_entities_for_suffix('ieeg', 'photo')
                if 'task' in required_entities:
                    entities["task"] = task
            elif modality in anatomical_modalities:
                # Anatomical files - extract suffix and check schema
                suffix = modality.split('(')[0].strip()  # e.g., "T1w (anat)" -> "T1w"
                required_entities = bids_subject.get_required_entities_for_suffix('anat', suffix)
                if 'task' in required_entities:
                    entities["task"] = task

            if file.get("acquisition", ""):
                entities["acq"] = file.get("acquisition")
            if file.get("reconstruction", ""):
                entities["rec"] = file.get("reconstruction")
            if file.get("contrast_agent", ""):
                entities["ce"] = file.get("contrast_agent")

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

            # Update overall progress across all subjects
            processed_files += 1
            overall_progress = round(100 * (float(processed_files) / total_files))
            conn.send(overall_progress)  # Send overall progress to the main thread

    bids_folder.generate_participants_tsv()
    conn.send(PROGRESS_DONE)  # Indicate completion
