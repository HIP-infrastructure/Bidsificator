import os
from pathlib import Path
import glob
import yaml

class DataCrawler:
    def __init__(self, config_file):
        self.config_data = self.__read_config_file(config_file)
        self.db_path = self.config_data['db_path']
        self.subject_pattern = self.config_data['subject_structure']['subject_pattern']
        self.data_types = self.config_data['subject_structure']['data_types']

    def __expand_path(self, path_pattern):
        """Expand wildcard patterns in the given path."""
        return glob.glob(path_pattern)

    def __find_subject_dirs(self, base_paths, subject_pattern):
        """Find subject directories based on the given base paths and pattern."""
        subject_dirs = set()
        for base_path in base_paths:
            expanded_paths = self.__expand_path(base_path)
            for path in expanded_paths:
                subject_dirs.update(glob.glob(os.path.join(path, subject_pattern)))
        return list(subject_dirs)

    def __get_or_create_subject_data(self, subjects_data, subject_id):
        """Get existing subject data or create a new one if not found."""
        for subject_data in subjects_data:
            if subject_data["subject_id"] == subject_id:
                return subject_data
        new_subject_data = {"subject_id": subject_id, "data": {}}
        subjects_data.append(new_subject_data)
        return new_subject_data

    def __read_config_file(self, file_path):
        with open(file_path, 'r') as file:
            config_data = yaml.safe_load(file)
        return config_data

    def __get_subject_dirs(self):
        """Find subject directories based on the given base paths and pattern."""
        same_folder = self.db_path['anatomical'] == self.db_path['functional']
        if same_folder:
            return self.__find_subject_dirs([self.db_path['anatomical']], self.subject_pattern)
        else:
            anatomical_subject_dirs = self.__find_subject_dirs([self.db_path['anatomical']], self.subject_pattern)
            functional_subject_dirs = self.__find_subject_dirs([self.db_path['functional']], self.subject_pattern)
            # Merge the lists and remove duplicates
            return list(set(anatomical_subject_dirs + functional_subject_dirs))

    def __guess_modality(self, data_info):
        description = data_info['description'].lower()
        modality_map = {
            'intracranial': 'ieeg (ieeg)',
            't1-weighted': 'T1w (anat)',
            't2-weighted': 'T2w (anat)',
            'ct': 'CT (anat)',
            't1rho': 'T1rho (anat)',
            't1p': 'T1rho (anat)',
            't2star': 'T2star (anat)'
        }

        for keyword, modality in modality_map.items():
            if keyword in description:
                return modality

        return ''

    def process_subject_data(self):
        """Process data for each subject directory."""
        subject_dirs = self.__get_subject_dirs()
        subjects_data = []
        for subject_dir in subject_dirs:
            subject_id = Path(subject_dir).name
            subject_data = self.__get_or_create_subject_data(subjects_data, subject_id)

            for data_type, data_info in self.data_types.items():
                data_type_dir = data_info['directory']
                # If the data_type directory contains a placeholder, replace it with the subject pattern
                if '${subject_pattern}' in data_type_dir:
                    data_type_dir = data_type_dir.replace('${subject_pattern}', subject_id)

                # Expand data_type_dir if it contains wildcards
                expanded_dirs = self.__expand_path(os.path.join(subject_dir, data_type_dir))
                for expanded_dir in expanded_dirs:
                    for file_extension in data_info['file_extensions']:
                        search_path = os.path.join(expanded_dir, '*' + file_extension)
                        found_files = glob.glob(search_path)
                        if found_files:
                            if data_type not in subject_data["data"]:
                                subject_data["data"][data_type] = {
                                    "description": data_info['description'],
                                    "modality": self.__guess_modality(data_info),
                                    "file_paths": found_files
                                }
                            else:
                                subject_data["data"][data_type]["file_paths"].extend(found_files)
        return subjects_data

    @staticmethod
    def crawl_data(yaml_file):
        crawler = DataCrawler(yaml_file)
        subjects_data = crawler.process_subject_data()
        return subjects_data
