import os
import shutil

import dicom2nifti

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
):
    temp_dir = "/tmp/mri_conversion"
    os.makedirs(temp_dir, exist_ok=True)

    # Calculate total files across all subjects for overall progress
    total_files = sum(len(subject['files']) for subject in subjects_list)
    processed_files = 0
    
    
    bids_folder = BidsFolder(dataset_path)
    for subject in subjects_list:
        try:
            bids_subject = bids_folder.add_bids_subject(
                "sub-" + subject['subject_id'], 
                subject_description={'age' : '123', 'sex' : 'M/F'},
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

            # Define entities for the file
            entities={
                "sub": bids_subject.get_subject_id(),
                "ses": file.get("session", ""),
                "task": file.get("task", ""),
                "acq": file.get("acquisition", ""),
                "rec": file.get("reconstruction", ""),
                "ce": file.get("contrast_agent", "")
            }

            # Process file based on its modality
            modality = file.get("modality", "")
            if modality == "ieeg (ieeg)":
                try:
                    new_file_path = bids_subject.add_functionnal_file(file_path, entities)
                    bids_subject.generate_events_file(new_file_path, entities)
                    bids_subject.generate_channels_file(new_file_path, entities)
                    bids_subject.generate_task_file(new_file_path, entities)
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
                    print(f"Skipping file")
            elif modality == "photo (ieeg)":
                try:
                    bids_subject.add_photo_file(file_path, entities["ses"], entities["acq"])
                except Exception as e:
                    print(f"Error processing photo file {file_path}: {e}")
                    print(f"Skipping file")
            elif modality in anatomical_modalities:
                #If it's an anat folder, probably need to convert
                if os.path.isdir(file_path):
                    dicom2nifti.convert_directory(file_path, temp_dir, compression=False)
                    file_names = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
                    #if one element in folder
                    if len(file_names) == 1:
                        file_path = temp_dir + os.sep + file_names[0]
                        bids_subject.add_anatomical_file(file_path, entities, str(modality).replace(" (anat)", ""))
                        os.remove(file_path)
                else:
                    bids_subject.add_anatomical_file(file_path, entities, str(modality).replace(" (anat)", ""))
                print("adding anatomical file")
            else:
                print("modality not recognized : ", modality)

            # Update overall progress across all subjects
            processed_files += 1
            overall_progress = round(100 * (float(processed_files) / total_files))
            conn.send(overall_progress)  # Send overall progress to the main thread

    bids_folder.generate_participants_tsv()
    shutil.rmtree(temp_dir)
    conn.send(101)  # Indicate completion
