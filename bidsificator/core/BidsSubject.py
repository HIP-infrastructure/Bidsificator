import re
import csv
import json
import shutil
import platform
from pathlib import Path

# Deal with the dependency from PyEEGFormat according to os
os_name= platform.system()
machine = platform.machine()

if os_name == "Darwin":
    if 'x86_64' in machine.lower():
        raise Exception(f"Lib not build at the moment: {os_name}")
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
    def __init__(self, parent_path, subject_id, optional_keys=None):
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

    def get_subject_id(self):
        return self.__subject_id

    def get_anat_post_path(self):
        return str(self.__anat_post_path) + "/"

    def get_func_post_path(self):
        return str(self.__func_post_path) + "/"

    def get_anat_pre_path(self):
        return str(self.__anat_pre_path) + "/"

    def get_func_pre_path(self):
        return str(self.__func_pre_path) + "/"
    
    def get_optional_keys(self):
        return self.__optional_keys_dict if self.__optional_keys_dict is not None else {}

    @staticmethod
    def define_bids_functionnal_string(subject_entities):
        bids_name = subject_entities["sub"]
        if "ses" in subject_entities and subject_entities["ses"]:
            bids_name += "_ses-" + subject_entities["ses"]
        if "task" in subject_entities and subject_entities["task"]:
            bids_name += "_task-" + subject_entities["task"]
        if "acq" in subject_entities and subject_entities["acq"]:
            bids_name += "_acq-" + subject_entities["acq"]
        return bids_name

    def add_functionnal_file(self, file_path, file_entities):
        # Convert file_path to a Path object and get the suffix
        file_path = Path(file_path)
        file_suffix = file_path.suffix.lower()

        bids_name_nosuffix = BidsSubject.define_bids_functionnal_string(file_entities) + "_ieeg"

        # Create new_file_name based on the file_suffix
        if file_suffix == ".trc":
            new_file_name = str(bids_name_nosuffix) + ".vhdr"
        else:
            new_file_name = str(bids_name_nosuffix) + file_suffix

        new_file_path = Path(self.get_func_post_path()) / new_file_name

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
    
    def generate_events_file(self, eeg_file_path, file_entities):
        base_file_path = str(self.get_func_post_path() + BidsSubject.define_bids_functionnal_string(file_entities))
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
    
    def generate_channels_file(self, eeg_file_path, file_entities):
        base_file_path = str(self.get_func_post_path() + BidsSubject.define_bids_functionnal_string(file_entities))
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

    def generate_task_file(self, eeg_file_path, file_entities):
        base_file_path = str(self.get_func_post_path() + BidsSubject.define_bids_functionnal_string(file_entities))
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
    def define_bids_string_nonparametric_structural_mri(subject_entities):
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

    def add_anatomical_file(self, file_path, file_struct, modality):
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

    def delete_bids_file(self, file_full_path):
        if not isinstance(file_full_path, Path):
            file_full_path = Path(file_full_path)
        if file_full_path.exists():
            file_full_path.unlink()
        else:
            print("File not found : ", file_full_path)