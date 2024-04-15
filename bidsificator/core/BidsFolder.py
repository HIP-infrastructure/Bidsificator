import csv
import json
import shutil
from pathlib import Path
from typing import Optional

from core.BidsSubject import BidsSubject

class BidsFolder:
    def __init__(self, root_path: str):
        if not isinstance(root_path, Path):
            root_path = Path(root_path)
        self.__path = root_path
        self.__path.mkdir(parents=True, exist_ok=True)
        self.__bids_subjects = []

        #read participants.tsv if it exists and return a list of subject_id and their optional keys
        participants_tsv_path = self.__path / "participants.tsv"
        if participants_tsv_path.exists():
            with open(participants_tsv_path, 'r') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    subject_id = row["participant_id"]
                    subject_optional_keys = {k: v for k, v in row.items() if k != "participant_id"}
                    self.__bids_subjects.append(BidsSubject(self.__path, subject_id, subject_optional_keys))

    def create_folders(self):
        code_path = self.__path / "code"
        code_path.mkdir(parents=True, exist_ok=True)
        derivatives_path = self.__path / "derivatives"
        derivatives_path.mkdir(parents=True, exist_ok=True)

    def generate_empty_dataset_description_file(self, dataset_name: str, json_file_path: str):
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

    def generate_dataset_description_file(self, dataset_description_dict: dict, json_file_path: str):
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

    def add_bids_subject(self, subject_id: str, subject_description: dict):
        new_subject = BidsSubject(self.__path, subject_id, subject_description)
        self.__bids_subjects.append(new_subject)
        return new_subject
    
    def delete_bids_subject(self, subject_id: str):
        for subject in self.__bids_subjects:
            if subject.get_subject_id() == subject_id:
                #Remove subject from list
                self.__bids_subjects.remove(subject)
                #Remove subject folder from disk
                subject_to_delete = self.__path / subject_id
                shutil.rmtree(subject_to_delete)
                print("Subject " + subject_id + " deleted")
                return 
        print("Subject " + subject_id + " not found")

    def get_bids_subject(self, subject_id: str) -> Optional[BidsSubject]:
        return next((x for x in self.__bids_subjects if x.get_subject_id() == subject_id), None)
    
    def get_bids_subects(self) -> Optional[BidsSubject]:
        return self.__bids_subjects
    
    def generate_participants_tsv(self, participants_tsv_path: str = ""):        
        if not participants_tsv_path:
            participants_tsv_path = self.__path / "participants.tsv"

        #get all subjects and make a dict of all their optional keys and remove duplicate
        all_optional_keys = list({key: None for subject in  self.__bids_subjects for key in subject.get_optional_keys().keys()})

        #open participants_tsv file and write the header
        with open(participants_tsv_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            print(str(["participant_id"] + all_optional_keys))
            writer.writerow(["participant_id"] + all_optional_keys)
            for subject in self.__bids_subjects:
                row = [subject.get_subject_id()]
                for key in all_optional_keys:
                    row.append(subject.get_optional_keys().get(key, ""))
                writer.writerow(row)