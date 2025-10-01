import csv
import json
import shutil
from pathlib import Path
from typing import Optional

from .BidsSubjectSchema import BidsSubject
from .schema import BidsSchemaManager


class BidsFolder:
    def __init__(self, root_path: str):
        if not isinstance(root_path, Path):
            root_path = Path(root_path)
        self.__path = root_path
        self.__path.mkdir(parents=True, exist_ok=True)
        self.__bids_subjects = []
        
        # Initialize schema manager for schema-driven operations (singleton)
        self.schema_manager = BidsSchemaManager.get_instance()

        #read participants.tsv if it exists and return a list of subject_id and their optional keys
        participants_tsv_path = self.__path / "participants.tsv"
        if participants_tsv_path.exists():
            with open(participants_tsv_path, 'r') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    subject_id = row["participant_id"]
                    subject_optional_keys = {k: v for k, v in row.items() if k != "participant_id"}
                    
                    # Extract subject ID without 'sub-' prefix for new BidsSubject constructor
                    # Old constructor expected full folder name (sub-coucou11), new expects just ID (coucou11)
                    clean_subject_id = subject_id.replace("sub-", "") if subject_id.startswith("sub-") else subject_id
                    
                    bids_subject = BidsSubject(clean_subject_id, self.__path, self.schema_manager)
                    # Store optional metadata in the subject instance
                    bids_subject.optional_metadata.update(subject_optional_keys)
                    self.__bids_subjects.append(bids_subject)

    def create_folders(self):
        code_path = self.__path / "code"
        code_path.mkdir(parents=True, exist_ok=True)
        derivatives_path = self.__path / "derivatives"
        derivatives_path.mkdir(parents=True, exist_ok=True)
        
        # Generate required README file for BIDS compliance
        self.generate_readme_file()

    def generate_empty_dataset_description_file(self, dataset_name: str, json_file_path: str):
        # Get BIDS version from schema instead of hardcoding
        bids_version = self.schema_manager.get_bids_version()

        dataset_description = {
            "Name": dataset_name,
            "BIDSVersion": bids_version,
            "DatasetType": "raw",
            "License": "n/a",
            "Authors": [],
            "Acknowledgements": "n/a",
            "HowToAcknowledge": "n/a",
            "Funding": [],
            "ReferencesAndLinks": [],
            "DatasetDOI": "n/a",
            "GeneratedBy": [
                {
                    "Name": "Bidsificator",
                    "Version": "unknown",
                    "Description": "BIDS dataset created using Bidsificator"
                }
            ],
            "SourceDatasets": []
        }

        with open(json_file_path, 'w') as f:
            json.dump(dataset_description, f, indent=4)

    def generate_dataset_description_file(self, dataset_description_dict: dict, json_file_path: str = ""):
        if not json_file_path:
            json_file_path = self.__path / "dataset_description.json"

        # Get BIDS version from schema if not provided in input dict
        default_bids_version = self.schema_manager.get_bids_version()

        dataset_description_dict = {
            "Name": dataset_description_dict.get("Name", "n/a"),
            "BIDSVersion": dataset_description_dict.get("BIDSVersion", default_bids_version),
            "DatasetType": dataset_description_dict.get("DatasetType", "raw"),
            "License": dataset_description_dict.get("License", "n/a"),
            "Authors": dataset_description_dict.get("Authors", []),
            "Acknowledgements": dataset_description_dict.get("Acknowledgements", "n/a"),
            "HowToAcknowledge": dataset_description_dict.get("HowToAcknowledge", "n/a"),
            "Funding": dataset_description_dict.get("Funding", []),
            "ReferencesAndLinks": dataset_description_dict.get("ReferencesAndLinks", []),
            "DatasetDOI": dataset_description_dict.get("DatasetDOI", "n/a"),
            "GeneratedBy": dataset_description_dict.get("GeneratedBy", [
                {
                    "Name": "Bidsificator",
                    "Version": "unknown",
                    "Description": "BIDS dataset created using Bidsificator"
                }
            ]),
            "SourceDatasets": dataset_description_dict.get("SourceDatasets", [])
        }

        with open(json_file_path, 'w') as f:
            json.dump(dataset_description_dict, f, indent=4)

    def generate_readme_file(self, readme_path: str = ""):
        """Generate a README file for BIDS compliance"""
        if not readme_path:
            readme_path = self.__path / "README"
        
        readme_content = f"""# {self.get_dataset_name()}

## Dataset Description

This BIDS dataset was created using Bidsificator.

## Data Acquisition

Please provide information about data acquisition parameters, equipment used, and experimental procedures.

## Participants

Please provide information about the participants included in this dataset.

## Code and Analysis

Analysis code and processing scripts can be found in the `code/` directory.

## Notes

Please update this README file with specific information about your dataset, including:
- Detailed description of the experimental paradigm
- Information about data collection procedures  
- Preprocessing steps applied
- Any relevant methodological details
- Contact information for questions

## License

Please specify the license under which this data is shared.
"""
        
        with open(readme_path, 'w') as f:
            f.write(readme_content)

    def rename_dataset(self, new_dataset_name: str):
        self.__path.rename(self.__path.parent / new_dataset_name)
        self.__path = self.__path.parent / new_dataset_name

    def get_dataset_name(self) -> str:
        return self.__path.name

    def add_bids_subject(self, subject_id: str, subject_description: dict, overwrite: bool = False):
        """
        Add a new BIDS subject to the dataset.
        
        Args:
            subject_id: The subject identifier
            subject_description: Dictionary containing subject metadata
            overwrite: If True, overwrites existing subject; if False, raises error for duplicates
            
        Returns:
            BidsSubject: The created subject instance
            
        Raises:
            ValueError: If subject already exists and overwrite=False
        """
        existing_subject = next((s for s in self.__bids_subjects if s.get_subject_id() == subject_id), None)
        
        if existing_subject:
            if overwrite:
                # Remove existing subject before creating new one
                self.delete_bids_subject(subject_id)
            else:
                raise ValueError(f"A subject with ID {subject_id} already exists.")

        new_subject = BidsSubject(subject_id, self.__path, self.schema_manager)
        # Store optional metadata in the subject instance
        new_subject.optional_metadata.update(subject_description)
        self.__bids_subjects.append(new_subject)
        return new_subject

    def delete_bids_subject(self, subject_id: str):
        for subject in self.__bids_subjects:
            if subject.get_subject_id() == subject_id:
                #Remove subject from list
                self.__bids_subjects.remove(subject)
                #Remove subject folder from disk
                subject_to_delete = self.__path / f"sub-{subject_id}"
                shutil.rmtree(subject_to_delete)
                return

    def get_bids_subject(self, subject_id: str) -> Optional[BidsSubject]:
        return next((x for x in self.__bids_subjects if x.get_subject_id() == subject_id), None)

    def get_bids_subjects(self) -> Optional[BidsSubject]:
        return self.__bids_subjects
    
    def subject_exists(self, subject_id: str) -> bool:
        """Check if a subject with the given ID already exists."""
        return any(subject.get_subject_id() == subject_id for subject in self.__bids_subjects)
    
    def find_existing_subjects(self, subject_ids: list[str]) -> list[str]:
        """Return a list of subject IDs that already exist in the dataset."""
        existing_ids = []
        for subject_id in subject_ids:
            if self.subject_exists(subject_id):
                existing_ids.append(subject_id)
        return existing_ids

    def generate_participants_tsv(self, participants_tsv_path: str = ""):
        if not participants_tsv_path:
            participants_tsv_path = self.__path / "participants.tsv"

        #get all subjects and make a dict of all their optional keys and remove duplicate
        all_optional_keys = list({key: None for subject in  self.__bids_subjects for key in subject.get_optional_keys().keys()})

        #open participants_tsv file and write the header
        with open(participants_tsv_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(["participant_id"] + all_optional_keys)
            for subject in self.__bids_subjects:
                # participant_id should have 'sub-' prefix for BIDS compliance
                participant_id = f"sub-{subject.get_subject_id()}"
                row = [participant_id]
                for key in all_optional_keys:
                    row.append(subject.get_optional_keys().get(key, ""))
                writer.writerow(row)
