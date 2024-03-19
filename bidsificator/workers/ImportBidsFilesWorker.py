from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime
from core.BidsFolder import BidsFolder

import os
import shutil
import dicom2nifti

class ImportBidsFilesWorker(QObject):
    update_progressbar_signal = pyqtSignal(int)
    finished = pyqtSignal()
    __dataset_path = ""
    __subject_name = ""
    __file_list = []
    __anatomical_modalities = {"T1w (anat)", "T2w (anat)", "T1rho (anat)", "T2rho (anat)", "FLAIR (anat)"}

    def __init__(self, dataset_path, subject_name, file_list):
        super().__init__()
        self.__dataset_path = dataset_path
        self.__subject_name = subject_name
        self.__file_list = file_list

    def Process(self):
        print("Processing in " + self.__dataset_path)
        
        bids_folder = BidsFolder(self.__dataset_path)
        bids_subject = bids_folder.get_bids_subject(self.__subject_name)
        if bids_subject is None:
            print("Subject not found")
            return
        
        # Create a temporary directory to store converted files
        temp_dir = '/tmp/mri_conversion'
        os.makedirs(temp_dir, exist_ok=True)    

        percentage = 0
        current_file = 1
        self.update_progressbar_signal.emit(percentage)
        # Process each file in the file list
        for file in self.__file_list:
            file_path = file["file_path"]

            # Skip if file does not exist        
            if not os.path.exists(file_path):
                print(f"File {file_path} does not exist. Skipping.")
                continue

            # Define entities for the file
            entities={
                "sub": self.__subject_name,
                "ses": file.get("session", ""),
                "task": file.get("task", ""),
                "acq": file.get("acquisition", ""),
                "rec": file.get("reconstruction", ""),
                "ce": file.get("contrast_agent", "")
            }

            # Process file based on its modality
            modality = file.get("modality", "")
            if modality == "ieeg (ieeg)":
                new_file_path = bids_subject.add_functionnal_file(file_path, entities)
                bids_subject.generate_events_file(new_file_path, entities)
                bids_subject.generate_channels_file(new_file_path, entities)
                bids_subject.generate_task_file(new_file_path, entities)
            elif modality in self.__anatomical_modalities:
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
                    bids_subject.add_anatomical_file(file_path, file)
                print("adding anatomical file")
            else:
                print("modality not recognized : ", modality)

            percentage = round(100 * (float(current_file) / len(self.__file_list)))
            current_file += 1
            self.update_progressbar_signal.emit(percentage)
        
        # Clean up temporary directory
        shutil.rmtree(temp_dir)

        self.finished.emit()