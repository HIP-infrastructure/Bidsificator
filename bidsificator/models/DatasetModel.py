"""Model for managing BIDS dataset operations and metadata."""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path


@dataclass 
class DatasetInfo:
    """Information about a BIDS dataset."""
    name: str
    path: str
    description: Dict[str, Any] = field(default_factory=dict)
    participants: List[Dict[str, str]] = field(default_factory=list)
    is_valid: bool = False
    validation_level: str = "NOT_BIDS"  # STRICT_BIDS, PARTIAL_BIDS, NOT_BIDS
    validation_issues: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate and process dataset info after initialization."""
        if not self.name:
            self.name = os.path.basename(self.path) if self.path else "Unnamed Dataset"
    
    def get_dataset_description_path(self) -> str:
        """Get path to dataset_description.json."""
        return os.path.join(self.path, "dataset_description.json")
    
    def get_participants_path(self) -> str:
        """Get path to participants.tsv."""
        return os.path.join(self.path, "participants.tsv")
    
    def has_required_files(self) -> bool:
        """Check if dataset has required BIDS files."""
        required_files = [
            self.get_dataset_description_path(),
            self.get_participants_path()
        ]
        return all(os.path.exists(f) for f in required_files)


class DatasetModel:
    """Model for managing BIDS dataset operations."""
    
    def __init__(self):
        """Initialize dataset model."""
        self._current_dataset: Optional[DatasetInfo] = None
        self._subjects: List[str] = []
        self._sessions: Dict[str, List[str]] = {}  # subject_id -> list of sessions
        self._is_loaded = False
    
    @property
    def current_dataset(self) -> Optional[DatasetInfo]:
        """Get current dataset info."""
        return self._current_dataset
    
    @property
    def is_loaded(self) -> bool:
        """Check if a dataset is currently loaded."""
        return self._is_loaded and self._current_dataset is not None
    
    @property
    def dataset_path(self) -> str:
        """Get current dataset path."""
        return self._current_dataset.path if self._current_dataset else ""
    
    @property
    def dataset_name(self) -> str:
        """Get current dataset name."""
        return self._current_dataset.name if self._current_dataset else ""
    
    @property
    def subjects(self) -> List[str]:
        """Get list of subject IDs in dataset."""
        return self._subjects.copy()
    
    @property
    def validation_level(self) -> str:
        """Get current dataset validation level."""
        return self._current_dataset.validation_level if self._current_dataset else "NOT_BIDS"
    
    @property
    def validation_issues(self) -> List[str]:
        """Get current dataset validation issues."""
        return self._current_dataset.validation_issues if self._current_dataset else []
    
    def create_dataset(self, dataset_path: str, dataset_name: str) -> Tuple[bool, str]:
        """
        Create a new BIDS dataset.
        
        Args:
            dataset_path: Path where dataset should be created
            dataset_name: Name for the dataset
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            from ..core.BidsFolder import BidsFolder
            from ..core.BidsUtilityFunctions import BidsUtilityFunctions
            
            # Clean the dataset name and create unique path
            clean_name = BidsUtilityFunctions.clean_string(dataset_name)
            full_path = os.path.join(dataset_path, clean_name)
            unique_path = BidsUtilityFunctions.get_unique_path(full_path)
            final_name = os.path.basename(unique_path).replace("_", " ")
            
            # Create BIDS folder structure
            bids_folder = BidsFolder(unique_path)
            bids_folder.create_folders()
            
            # Generate required files
            description_path = os.path.join(unique_path, "dataset_description.json")
            bids_folder.generate_empty_dataset_description_file(final_name, description_path)
            bids_folder.generate_participants_tsv()
            
            # Load the newly created dataset
            return self.load_dataset(unique_path)
            
        except Exception as e:
            return False, f"Failed to create dataset: {str(e)}"
    
    def _validate_bids_structure(self, dataset_path: str) -> Dict[str, Any]:
        """
        Validate BIDS dataset structure and return validation results.
        
        Args:
            dataset_path: Path to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'level': 'NOT_BIDS',
            'is_valid': False,
            'issues': [],
            'warnings': []
        }
        
        # Check 1: Required files
        desc_file = os.path.join(dataset_path, "dataset_description.json")
        participants_file = os.path.join(dataset_path, "participants.tsv")
        
        has_description = os.path.exists(desc_file)
        has_participants = os.path.exists(participants_file)
        
        if not has_description:
            validation_result['issues'].append("Missing required file: dataset_description.json")
        
        if not has_participants:
            validation_result['issues'].append("Missing required file: participants.tsv")
        
        # Check 2: Subject folders
        try:
            entries = os.listdir(dataset_path)
            subject_folders = [e for e in entries 
                             if os.path.isdir(os.path.join(dataset_path, e)) 
                             and e.startswith("sub-")]
            
            if not subject_folders:
                validation_result['issues'].append("No BIDS subject folders (sub-*) found")
            
            # Check 3: Optional but recommended files
            readme_file = os.path.join(dataset_path, "README")
            readme_md_file = os.path.join(dataset_path, "README.md")
            if not (os.path.exists(readme_file) or os.path.exists(readme_md_file)):
                validation_result['warnings'].append("README file is recommended but not found")
            
            # Determine validation level
            # A valid BIDS dataset must have dataset_description.json and participants.tsv
            # Subject folders are optional for newly created datasets
            if has_description and has_participants:
                validation_result['level'] = 'STRICT_BIDS'
                validation_result['is_valid'] = True
                if not subject_folders:
                    validation_result['warnings'].append("No subjects found - this is normal for new datasets")
            elif has_description or has_participants:
                validation_result['level'] = 'PARTIAL_BIDS'
                validation_result['is_valid'] = False
            else:
                validation_result['level'] = 'NOT_BIDS'
                validation_result['is_valid'] = False
                
        except Exception as e:
            validation_result['issues'].append(f"Error scanning directory: {str(e)}")
        
        return validation_result
    
    def load_dataset(self, dataset_path: str) -> Tuple[bool, str]:
        """
        Load an existing BIDS dataset.
        
        Args:
            dataset_path: Path to the dataset root
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not os.path.exists(dataset_path):
                return False, "Dataset path does not exist"
            
            if not os.path.isdir(dataset_path):
                return False, "Dataset path is not a directory"
            
            # Create dataset info
            dataset_name = os.path.basename(dataset_path)
            dataset_info = DatasetInfo(name=dataset_name, path=dataset_path)
            
            # Validate BIDS structure
            validation_result = self._validate_bids_structure(dataset_path)
            dataset_info.validation_level = validation_result['level']
            dataset_info.validation_issues = validation_result['issues']
            dataset_info.validation_warnings = validation_result['warnings']
            dataset_info.is_valid = validation_result['is_valid']
            
            # Load dataset description if it exists
            desc_path = dataset_info.get_dataset_description_path()
            if os.path.exists(desc_path):
                try:
                    with open(desc_path, 'r') as f:
                        dataset_info.description = json.load(f)
                    # Update name from description if available
                    if 'Name' in dataset_info.description:
                        dataset_info.name = dataset_info.description['Name']
                except Exception:
                    pass  # Continue with default name if description can't be loaded
            
            # Load subjects
            self._load_subjects(dataset_path)
            
            # Set as current dataset
            self._current_dataset = dataset_info
            self._is_loaded = True
            
            return True, ""
            
        except Exception as e:
            return False, f"Failed to load dataset: {str(e)}"
    
    def _load_subjects(self, dataset_path: str):
        """Load subjects from dataset directory."""
        try:
            from ..core.BidsFolder import BidsFolder
            
            # Use BidsFolder to get subjects
            bids_folder = BidsFolder(dataset_path)
            bids_subjects = bids_folder.get_bids_subjects()
            
            # Extract subject IDs
            self._subjects = [subject.get_subject_id() for subject in bids_subjects]
            
            # If BidsFolder found no subjects, fall back to directory scanning
            if not self._subjects:
                raise RuntimeError("No subjects found in BidsFolder, falling back to directory scan")
            
            # Load sessions for each subject
            self._sessions = {}
            for subject in bids_subjects:
                subject_id = subject.get_subject_id()
                subject_path = os.path.join(dataset_path, f"sub-{subject_id}")
                if os.path.exists(subject_path):
                    sessions = [f for f in os.listdir(subject_path)
                              if os.path.isdir(os.path.join(subject_path, f))
                              and f.startswith("ses-") and not f.startswith(".")]
                    self._sessions[subject_id] = sessions
                else:
                    self._sessions[subject_id] = []
                    
        except Exception:
            # Fallback: scan directory directly
            self._subjects = []
            self._sessions = {}
            
            try:
                items = os.listdir(dataset_path)
                for item in items:
                    item_path = os.path.join(dataset_path, item)
                    if (os.path.isdir(item_path) and 
                        item.startswith("sub-") and 
                        not item.startswith(".")):
                        # Strip 'sub-' prefix to be consistent with main code path
                        subject_id = item[4:] if item.startswith("sub-") else item
                        self._subjects.append(subject_id)
                        
                        # Load sessions
                        sessions = [f for f in os.listdir(item_path)
                                   if os.path.isdir(os.path.join(item_path, f))
                                   and f.startswith("ses-") and not f.startswith(".")]
                        self._sessions[subject_id] = sessions
            except Exception:
                pass  # Continue with empty lists
    
    def get_sessions_for_subject(self, subject_id: str) -> List[str]:
        """
        Get sessions for a specific subject.
        
        Args:
            subject_id: Subject ID to get sessions for
            
        Returns:
            List of session names
        """
        return self._sessions.get(subject_id, []).copy()
    
    def add_subject(self, subject_id: str) -> Tuple[bool, str]:
        """
        Add a new subject to the dataset.
        
        Args:
            subject_id: Subject ID to add
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._is_loaded:
            return False, "No dataset loaded"
        
        # Validate subject ID
        from ..services.ValidationServiceSchema import ValidationService
        validation_service = ValidationService()
        is_valid, error = validation_service.validate_subject_name(subject_id)
        if not is_valid:
            return False, error
        
        if subject_id in self._subjects:
            return False, "Subject already exists"
        
        try:
            # Create subject directory structure
            from ..core.BidsFolder import BidsFolder
            
            bids_folder = BidsFolder(self._current_dataset.path)
            subject_path = os.path.join(self._current_dataset.path, f"sub-{subject_id}")
            
            # This will be handled by the actual BIDS creation process
            # For now, just add to our internal list
            self._subjects.append(subject_id)
            self._sessions[subject_id] = []
            
            return True, ""
            
        except Exception as e:
            return False, f"Failed to add subject: {str(e)}"
    
    def validate_dataset(self, subject_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate the dataset or a specific subject.
        
        Args:
            subject_id: Optional subject ID to validate specifically
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not self._is_loaded:
            return False, "No dataset loaded"
        
        from ..services.ValidationServiceSchema import ValidationService
        validation_service = ValidationService()
        return validation_service.validate_bids_dataset(self._current_dataset.path, subject_id)
    
    def get_dataset_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the current dataset.
        
        Returns:
            Dictionary with dataset statistics
        """
        if not self._is_loaded:
            return {}
        
        total_sessions = sum(len(sessions) for sessions in self._sessions.values())
        subjects_with_sessions = sum(1 for sessions in self._sessions.values() if sessions)
        
        return {
            "name": self._current_dataset.name,
            "path": self._current_dataset.path,
            "is_valid": self._current_dataset.is_valid,
            "total_subjects": len(self._subjects),
            "total_sessions": total_sessions,
            "subjects_with_sessions": subjects_with_sessions,
            "has_required_files": self._current_dataset.has_required_files(),
            "subjects": self._subjects,
            "sessions": dict(self._sessions)
        }
    
    def refresh_subjects(self):
        """Refresh the subjects list from filesystem."""
        if self._is_loaded:
            self._load_subjects(self._current_dataset.path)
    
    def close_dataset(self):
        """Close the current dataset."""
        self._current_dataset = None
        self._subjects.clear()
        self._sessions.clear()
        self._is_loaded = False
    
    def get_tree_model_data(self) -> Optional[str]:
        """
        Get dataset path for tree view model.
        
        Returns:
            Dataset path or None if no dataset loaded
        """
        return self._current_dataset.path if self._is_loaded else None
    
    def update_participants_file(self) -> bool:
        """
        Update the participants.tsv file with current subjects.
        
        Returns:
            True if updated successfully
        """
        if not self._is_loaded:
            return False
        
        try:
            from ..core.BidsFolder import BidsFolder
            
            bids_folder = BidsFolder(self._current_dataset.path)
            bids_folder.generate_participants_tsv()
            return True
            
        except Exception:
            return False
    
