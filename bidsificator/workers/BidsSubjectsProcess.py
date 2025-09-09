import os

from ..core.BidsFolder import BidsFolder



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
            print(f"Skipping subject {subject['subject_id']}: {e}")
            continue
        
        if bids_subject is None:
            conn.send(-1)  # Indicate error
            return

        for index, file in enumerate(subject['files']):
            file_path = file["file_path"]

            # Skip if file does not exist
            if not os.path.exists(file_path):
                print(f"File {file_path} does not exist. Skipping.")
                continue

            # Define entities for the file, filtering out empty values
            entities = {}
            entities["sub"] = bids_subject.get_subject_id()
            
            if file.get("session", ""):
                entities["ses"] = file.get("session")
            
            # Process file based on its modality - use existing hardcoded approach for consistency
            modality = file.get("modality", "")
            
            # Use schema to determine if task is required for specific modality types
            # This is the schema-driven improvement while keeping existing patterns
            if modality == "ieeg (ieeg)":
                required_entities = bids_subject.get_required_entities_for_suffix('ieeg', 'ieeg')
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
                    print(f"Added iEEG file: {result.get('target_path', file_path)}")
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

            # Update overall progress across all subjects
            processed_files += 1
            overall_progress = round(100 * (float(processed_files) / total_files))
            conn.send(overall_progress)  # Send overall progress to the main thread

    bids_folder.generate_participants_tsv()
    conn.send(101)  # Indicate completion
