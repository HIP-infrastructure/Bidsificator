import os
import shutil
import dicom2nifti
from core.BidsFolder import BidsFolder

def processBidsFiles(conn, dataset_path: str, subject_name: str, file_list: list, anatomical_modalities: set[str]):
    temp_dir = '/tmp/mri_conversion'
    os.makedirs(temp_dir, exist_ok=True)

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

        progress = round(100 * (float(index + 1) / len(file_list)))
        conn.send(progress)  # Send progress to the main thread

    shutil.rmtree(temp_dir)
    conn.send(101)  # Indicate completion
