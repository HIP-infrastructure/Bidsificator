import os

from ..core.BidsFolder import BidsFolder


def processBidsFiles(
    conn,
    dataset_path: str,
    subject_name: str,
    file_list: list,
    anatomical_modalities: set[str],
):

    bids_folder = BidsFolder(dataset_path)
    bids_subject = bids_folder.get_bids_subject(subject_name)

    if bids_subject is None:
        conn.send(-1)  # Indicate error
        return

    for index, file in enumerate(file_list):
        file_path = file["file_path"]

        # Skip if file does not exist
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist. Skipping.")
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
                print(f"Added iEEG file: {result.get('target_path', file_path)}")
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                print(f"Skipping file")
        elif modality == "eeg (eeg)":
            try:
                # Map modality to datatype for schema-driven BidsSubject
                result = bids_subject.add_file(
                    source_path=file_path,
                    datatype='eeg',
                    entities=entities,
                    suffix='eeg'
                )
                print(f"Added EEG file: {result.get('target_path', file_path)}")
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                print(f"Skipping file")
        elif modality == "photo (ieeg)":
            try:
                # Photos are stored in ieeg datatype with photo suffix
                result = bids_subject.add_file(
                    source_path=file_path,
                    datatype='ieeg',
                    entities=entities,
                    suffix='photo'
                )
                print(f"Added photo file: {result.get('target_path', file_path)}")
            except Exception as e:
                print(f"Error processing photo file {file_path}: {e}")
                print(f"Skipping file")
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
                print(f"Added anatomical file: {result.get('target_path', file_path)}")
            except Exception as e:
                print(f"Error processing anatomical file {file_path}: {e}")
                print(f"Skipping file")
        else:
            print("modality not recognized : ", modality)

        progress = round(100 * (float(index + 1) / len(file_list)))
        conn.send(progress)  # Send progress to the main thread

    conn.send(101)  # Indicate completion
