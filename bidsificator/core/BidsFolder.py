import csv
import json
from pathlib import Path
import shutil

from core.BidsSubject import BidsSubject

class BidsFolder:
    def __init__(self, root_path):
        if not isinstance(root_path, Path):
            root_path = Path(root_path)
        self.__path = root_path
        self.__path.mkdir(parents=True, exist_ok=True)
        self.__bids_subjects = []
        for subject in self.__path.iterdir():
            if subject.is_dir() and subject.name.startswith("sub-"):
                self.__bids_subjects.append(BidsSubject(self.__path, subject.name))

    def create_folders(self):
        code_path = self.__path / "code"
        code_path.mkdir(parents=True, exist_ok=True)
        derivatives_path = self.__path / "derivatives"
        derivatives_path.mkdir(parents=True, exist_ok=True)

    def generate_empty_dataset_description_file(self, dataset_name, json_file_path):
        dataset_description = {
            "Name": dataset_name,
            "BIDSVersion": "1.2.0",
            "License": "n/a",
            "Authors": [],
            "Acknowledgements": "n/a",
            "HowToAcknowledge": "n/a",
            "Funding": [],
            "ReferencesAndLinks": [],
            "DatasetDOI": "n/a"
        }

        with open(json_file_path, 'w') as f:
            json.dump(dataset_description, f, indent=4)

    def generate_dataset_description_file(self, dataset_description_dict, json_file_path):
        # Extract values from the received dictionary
        #dataset_desc_json = dataset_description_dict["DatasetDescJSON"]
        dataset_description_dict = {
            "Name": dataset_description_dict.get("Name", "n/a"),
            "BIDSVersion": dataset_description_dict.get("BIDSVersion", "n/a"),
            "License": dataset_description_dict.get("License", "n/a"),
            "Authors": dataset_description_dict.get("Authors", []),
            "Acknowledgements": dataset_description_dict.get("Acknowledgements", "n/a"),
            "HowToAcknowledge": dataset_description_dict.get("HowToAcknowledge", "n/a"),
            "Funding": dataset_description_dict.get("Funding", []),
            "ReferencesAndLinks": dataset_description_dict.get("ReferencesAndLinks", []),
            "DatasetDOI": dataset_description_dict.get("DatasetDOI", "n/a")
        }

        # Write the new dictionary to the file
        with open(json_file_path, 'w') as f:
            json.dump(dataset_description_dict, f, indent=4)

    def add_bids_subject(self, subject_id):
        new_subject = BidsSubject(self.__path, subject_id)
        self.__bids_subjects.append(new_subject)
        return new_subject
    
    def delete_bids_subject(self, subject_id):
        subject_to_delete = self.__path / subject_id
        if subject_to_delete.exists():
            shutil.rmtree(subject_to_delete)
        else:
            print("Subject not found")

    def get_bids_subject(self, subject_id):
        return next((x for x in self.__bids_subjects if x.get_subject_id() == subject_id), None)
    
    def generate_participants_tsv(self, participants_tsv_path):
        print(self.__path)
        subjects = [x for x in self.__path.iterdir() if x.is_dir() and x.name.startswith("sub-")]
        with open(participants_tsv_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(["participant_id"])
            for subject in subjects:
                writer.writerow([subject.name])