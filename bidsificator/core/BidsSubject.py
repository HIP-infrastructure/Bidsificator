import os
import re
import csv
import json
import shutil
import platform
from pathlib import Path
from typing import Optional

# Deal with the dependency from PyEEGFormat according to os
os_name= platform.system()
machine = platform.machine()

if os_name == "Darwin":
    if 'x86_64' in machine.lower():
        from core.PyEEGFormat import wrappermac as wrapper
    elif 'arm' in machine.lower():
        from core.PyEEGFormat import wrappermacarm as wrapper
elif os_name == "Windows":
    from core.PyEEGFormat import wrapperwin as wrapper
elif os_name == "Linux":
    if 'x86_64' in machine.lower():
        from core.PyEEGFormat import wrapperlinux as wrapper
    elif 'arm' in machine.lower():
        from core.PyEEGFormat import wrapperlinuxarm64 as wrapper
else:
    raise Exception(f"Unsupported operating system: {os_name}")

class BidsSubject:
    def __init__(self, parent_path: str, subject_id: str, optional_keys:dict = None):
        if not isinstance(parent_path, Path):
            parent_path = Path(parent_path)
        self.__parent_path = parent_path
        self.__subject_id = subject_id
        self.__optional_keys_dict = optional_keys

        self.__subject_path = self.__parent_path / self.__subject_id
        self.__subject_path.mkdir(parents=True, exist_ok=True)

        self.__anat_post_path = self.__subject_path / "ses-post" / "anat"
        self.__func_post_path = self.__subject_path / "ses-post" / "ieeg"
        self.__anat_post_path.mkdir(parents=True, exist_ok=True)
        self.__func_post_path.mkdir(parents=True, exist_ok=True)

        self.__anat_pre_path = self.__subject_path / "ses-pre" / "anat"
        self.__func_pre_path = self.__subject_path / "ses-pre" / "ieeg"
        self.__anat_pre_path.mkdir(parents=True, exist_ok=True)
        self.__func_pre_path.mkdir(parents=True, exist_ok=True)

    def get_subject_id(self) -> str:
        return str(self.__subject_id)
       
    def set_subject_id(self, new_subject_id: str):
        """
        Set a new subject ID for the BidsSubject instance.
        This method updates the subject ID and renames the subject folder and all files recursively with the new subject ID.

        Args:
            new_subject_id (str): The new subject ID to be set.
        """
        # Check if the new subject ID is different from the current one
        if new_subject_id != self.__subject_id:
            # Rename all files recursively with the new subject ID
            for root, dirs, files in os.walk(self.__subject_path):
                for file in files:
                    old_file_path = os.path.join(root, file)
                    new_file_path = os.path.join(root, file.replace(self.__subject_id, new_subject_id))
                    os.rename(old_file_path, new_file_path)

            # Create the new subject path
            new_subject_path = self.__parent_path / new_subject_id

            # Rename the subject folder
            os.rename(self.__subject_path, new_subject_path)

            # Update the subject ID and subject path
            self.__subject_id = new_subject_id
            self.__subject_path = new_subject_path

            # Update the folder paths
            self.__anat_post_path = self.__subject_path / "ses-post" / "anat"
            self.__func_post_path = self.__subject_path / "ses-post" / "ieeg"
            self.__anat_pre_path = self.__subject_path / "ses-pre" / "anat"
            self.__func_pre_path = self.__subject_path / "ses-pre" / "ieeg"

    def get_anat_post_path(self) -> str:
        return str(self.__anat_post_path) + "/"

    def get_func_post_path(self) -> str:
        return str(self.__func_post_path) + "/"

    def get_anat_pre_path(self) -> str:
        return str(self.__anat_pre_path) + "/"

    def get_func_pre_path(self) -> str:
        return str(self.__func_pre_path) + "/"
    
    def get_optional_keys(self) -> dict:
        return self.__optional_keys_dict if self.__optional_keys_dict is not None else {}

    def add_optional_key(self, key, value = "n/a"):
        self.__optional_keys_dict[key] = value

    # Add a key at a specific position and keep the order
    def add_optional_key_at(self, position: int, key, value = "n/a"):
        items = list(self.__optional_keys_dict.items())
        items.insert(position, (key, value))
        self.__optional_keys_dict = dict(items)

    def remove_optional_key(self, key):
        if key in self.__optional_keys_dict:
            del self.__optional_keys_dict[key]
        else:
            print("Key not found : ", key)
            
    @staticmethod
    def define_bids_functionnal_string(subject_entities: dict) -> str:
        bids_name = subject_entities["sub"]
        if "ses" in subject_entities and subject_entities["ses"]:
            bids_name += "_ses-" + subject_entities["ses"]
        if "task" in subject_entities and subject_entities["task"]:
            bids_name += "_task-" + subject_entities["task"]
        if "acq" in subject_entities and subject_entities["acq"]:
            bids_name += "_acq-" + subject_entities["acq"]
        return bids_name

    def add_functionnal_file(self, file_path: str, file_entities: dict) -> Optional[str]:
        # Convert file_path to a Path object and get the suffix
        file_path = Path(file_path)
        file_suffix = file_path.suffix.lower()

        bids_name_nosuffix = BidsSubject.define_bids_functionnal_string(file_entities) + "_ieeg"

        # get Session folder path based on the ses entity
        session_folder = ""
        if file_entities["ses"] == "pre":
            session_folder = self.get_func_pre_path()
        elif file_entities["ses"] == "post":
            session_folder = self.get_func_post_path()
        else:
            print("Session not recognized : ", file_entities["ses"])
            return None

        # Create new_file_name based on the file_suffix
        if file_suffix == ".trc":
            new_file_name = bids_name_nosuffix + ".vhdr"
        else:
            new_file_name = bids_name_nosuffix + file_suffix

        # Create new_file_path
        new_file_path = Path(session_folder) / new_file_name

        if file_suffix == ".trc":
            print("Should convert file", file_path, "to", new_file_path)
            wrapper.convert_file(str(file_path).encode('utf-8'), str(new_file_path).encode('utf-8'))
            return str(new_file_path)
        elif file_suffix in [".vhdr", ".edf"]:
            print("Should copy file", file_path, "to", new_file_path)
            shutil.copy(file_path, new_file_path)
            return str(new_file_path)
        else:
            print("File extension not recognized : ", file_suffix)
            return None
    
    def add_photo_file(self, file_path: str, session:str = "", acquisition:str = ""):
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        file_suffix = file_path.suffix
        
        # get Session folder path based on parameters
        session_folder = ""
        if session == "pre":
            session_folder = self.get_func_pre_path()
        elif session == "post":
            session_folder = self.get_func_post_path()
        else:
            print("Session not recognized : ", session)
            return None
        
        # create destination file name 
        bids_name = self.__subject_id
        if session:
            bids_name += "_ses-" + session
        if acquisition:
            bids_name += "_acq-" + acquisition
        bids_name += "_photo" + file_suffix
        
        if file_suffix in [".jpg", ".png", ".tif"]: 
            print("Should copy file", file_path, "to", session_folder + bids_name)
            shutil.copy(file_path, self.get_func_post_path() + bids_name)
        else:    
            print("File extension not supported for bids photo files : ", file_suffix)

    def generate_events_file(self, eeg_file_path: str, file_entities: dict):
        base_file_path = str(Path(eeg_file_path).parent / BidsSubject.define_bids_functionnal_string(file_entities))
        tsv_file_path = base_file_path + "_events.tsv"
    
        PyIFile = wrapper.PyIFile(str(eeg_file_path).encode('utf-8'), False)
        sampling_frequency = PyIFile.get_sampling_frequency()
        trigger_count = PyIFile.get_trigger_count()
        with open(tsv_file_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(["onset", "duration", "trial_type", "response_time", "stim_file", "value"])
            for i in range(trigger_count):
                trigger = PyIFile.get_trigger(i)
                onset = trigger.Sample() / sampling_frequency
                writer.writerow([onset, "n/a", trigger.Sample(), trigger.Code(), "n/a", "n/a"])
    
    def generate_channels_file(self, eeg_file_path: str, file_entities: dict):
        base_file_path = str(Path(eeg_file_path).parent / BidsSubject.define_bids_functionnal_string(file_entities))
        tsv_file_path = base_file_path + "_channels.tsv"

        PyIFile = wrapper.PyIFile(str(eeg_file_path).encode('utf-8'), False)
        sampling_frequency = PyIFile.get_sampling_frequency()
        electrode_count = PyIFile.get_electrode_count()
        with open(tsv_file_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(["name", "type", "units", "low_cutoff", "high_cutoff", "reference" , "group" , "sampling_frequency" , "description" , "notch" , "status" , "status_description"])
            for i in range(electrode_count):
                electrode = PyIFile.get_electrode(i)
                site_name = electrode.Label()
                site_unit = electrode.Unit()
                lowpass_limit = electrode.PrefilteringLowPassLimit()
                highpass_limit = electrode.PrefilteringHighPassLimit()
                if re.match(r"^[A-Z]+\'*[0-9]{1,2}$", site_name):
                    electrode_name = re.sub(r'\d+', '', site_name)
                    writer.writerow([site_name, "SEEG", site_unit, lowpass_limit, highpass_limit, "intracranial", electrode_name, sampling_frequency, "n/a", 0, "good", "n/a"])

    def generate_task_file(self, eeg_file_path: str, file_entities: dict):
        base_file_path = str(Path(eeg_file_path).parent / BidsSubject.define_bids_functionnal_string(file_entities))
        json_file_path = base_file_path + "_ieeg.json"

        PyIFile = wrapper.PyIFile(str(eeg_file_path).encode('utf-8'), False)
        sampling_frequency = PyIFile.get_sampling_frequency()

        data = {
            "TaskName": "n/a",
            "InstitutionName": "n/a",
            "InstitutionAddress": "n/a",
            "Manufacturer": "n/a",
            "ManufacturersModelName": "n/a",
            "SoftwareVersions": "n/a",
            "TaskDescription": "n/a",
            "Instructions": "n/a",
            "DeviceSerialNumber": "unknown",
            "iEEGReference": "n/a",
            "SamplingFrequency": sampling_frequency,
            "PowerLineFrequency": 50,
            "SoftwareFilters": "n/a",
            "DCOffsetCorrection": "none",
            "HardwareFilters": "n/a",
            "ElectrodeManufacturer": "n/a",
            "ElectrodeManufacturersModelName": "n/a",
            "ECOGChannelCount": 0,
            "SEEGChannelCount": PyIFile.get_electrode_count(),
            "EEGChannelCount": 0,
            "EOGChannelCount": 0,
            "ECGChannelCount": 0,
            "EMGChannelCount": 0,
            "MiscChannelCount": 0,
            "TriggerChannelCount": 0,
            "RecordingDuration": 3, #TODO : get the real duration
            "RecordingType": "continuous",
            "EpochLength": 0,
            "iEEGGround": "n/a",
            "iEEGPlacementScheme": "n/a",
            "iEEGElectrodeGroups": "n/a",
            "SubjectArtefactDescription": "n/a",
            "ElectricalStimulation": False,
            "ElectricalStimulationParameters": "n/a"
        }

        with open(json_file_path, 'w') as f:
            json.dump(data, f, indent=4)
    
    @staticmethod
    def define_bids_string_nonparametric_structural_mri(subject_entities: dict) -> str:
        bids_name = subject_entities["sub"]
        if "ses" in subject_entities and subject_entities["ses"]:
            bids_name += "_ses-" + subject_entities["ses"]
        if "task" in subject_entities and subject_entities["task"]:
            bids_name += "_task-" + subject_entities["task"]
        if "acq" in subject_entities and subject_entities["acq"]:
            bids_name += "_acq-" + subject_entities["acq"]
        if "ce" in subject_entities and subject_entities["ce"]:
            bids_name += "_ce-" + subject_entities["ce"]
        if "rec" in subject_entities and subject_entities["rec"]:
            bids_name += "_rec-" + subject_entities["rec"]
        if "run" in subject_entities and subject_entities["run"]:
            bids_name += "_run-" + subject_entities["run"]        
        
        return bids_name

    def add_anatomical_file(self, file_path: str, file_struct: dict, modality: str):
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        file_suffix = file_path.suffix
        bids_name = BidsSubject.define_bids_string_nonparametric_structural_mri(file_struct) + "_" + modality + file_suffix
        if file_suffix == ".nii" or file_suffix == ".nii.gz":
            if file_struct["ses"] == "pre": 
                print("Should copy file", file_path, "to", self.get_anat_pre_path() + bids_name)
                shutil.copy(file_path, self.get_anat_pre_path() + bids_name)
            elif file_struct["ses"] == "post":
                print("Should copy file", file_path, "to", self.get_anat_post_path() + bids_name)
                shutil.copy(file_path, self.get_anat_post_path() + bids_name)
            else:
                print("Session not recognized : ", file_struct["ses"])
        else:    
            print("File extension not supported for bids anatomical files : ", file_suffix)

    def delete_bids_file(self, file_full_path: str):
        if not isinstance(file_full_path, Path):
            file_full_path = Path(file_full_path)
        if file_full_path.exists():
            file_full_path.unlink()
        else:
            print("File not found : ", file_full_path)