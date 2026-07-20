"""Model for managing subject data and batch import operations."""

import logging
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SubjectData:
    """Data structure for a subject with files."""
    subject_id: str
    files: List[Dict[str, str]] = field(default_factory=list)
    original_subject_id: Optional[str] = None  # For lookup table mapping
    display_name: Optional[str] = None  # For UI display
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not self.subject_id:
            raise ValueError("Subject ID cannot be empty")
    
    def add_file(self, file_data: Dict[str, str]):
        """Add a file to this subject."""
        if file_data not in self.files:
            self.files.append(file_data)
    
    def remove_file(self, file_path: str) -> bool:
        """
        Remove a file by path.
        
        Args:
            file_path: Path of file to remove
            
        Returns:
            True if removed, False if not found
        """
        for i, file_data in enumerate(self.files):
            if file_data.get("file_path") == file_path:
                self.files.pop(i)
                return True
        return False
    
    def get_file_count(self) -> int:
        """Get number of files for this subject."""
        return len(self.files)
    
    def get_modalities(self) -> List[str]:
        """Get list of unique modalities for this subject."""
        modalities = set()
        for file_data in self.files:
            if file_data.get("modality"):
                modalities.add(file_data["modality"])
        return list(modalities)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "subject_id": self.subject_id,
            "files": self.files.copy(),
            "original_subject_id": self.original_subject_id,
            "display_name": self.display_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubjectData':
        """Create from dictionary format."""
        return cls(
            subject_id=data.get("subject_id", ""),
            files=data.get("files", []),
            original_subject_id=data.get("original_subject_id"),
            display_name=data.get("display_name")
        )


class SubjectDataModel:
    """Model for managing multiple subjects and batch import operations."""
    
    def __init__(self):
        """Initialize subject data model."""
        self._subjects: List[SubjectData] = []
        self._selected_subject_index = -1
    
    @property
    def subjects(self) -> List[SubjectData]:
        """Get list of all subjects."""
        return self._subjects.copy()
    
    @property
    def selected_subject_index(self) -> int:
        """Get currently selected subject index."""
        return self._selected_subject_index
    
    @selected_subject_index.setter
    def selected_subject_index(self, index: int):
        """Set currently selected subject index."""
        if -1 <= index < len(self._subjects):
            self._selected_subject_index = index
        else:
            self._selected_subject_index = -1
    
    def add_subject(self, subject_data: SubjectData) -> bool:
        """
        Add a subject to the model.
        
        Args:
            subject_data: SubjectData instance to add
            
        Returns:
            True if added successfully, False if duplicate
        """
        # Check for duplicates
        if self.has_subject(subject_data.subject_id):
            return False
        
        self._subjects.append(subject_data)
        return True
    
    def remove_subject(self, index: int) -> bool:
        """
        Remove a subject by index.
        
        Args:
            index: Index of subject to remove
            
        Returns:
            True if removed successfully
        """
        if 0 <= index < len(self._subjects):
            self._subjects.pop(index)
            
            # Update selection after removal
            if self._selected_subject_index >= len(self._subjects):
                self._selected_subject_index = len(self._subjects) - 1
            if len(self._subjects) == 0:
                self._selected_subject_index = -1
                
            return True
        return False
    
    def remove_subject_by_id(self, subject_id: str) -> bool:
        """
        Remove a subject by ID.
        
        Args:
            subject_id: ID of subject to remove
            
        Returns:
            True if removed successfully
        """
        for i, subject in enumerate(self._subjects):
            if subject.subject_id == subject_id:
                return self.remove_subject(i)
        return False
    
    def has_subject(self, subject_id: str) -> bool:
        """
        Check if a subject ID already exists.
        
        Args:
            subject_id: Subject ID to check
            
        Returns:
            True if subject exists
        """
        return any(subject.subject_id == subject_id for subject in self._subjects)
    
    def get_subject(self, index: int) -> Optional[SubjectData]:
        """
        Get subject by index.
        
        Args:
            index: Index of subject to get
            
        Returns:
            SubjectData instance or None if invalid index
        """
        if 0 <= index < len(self._subjects):
            return self._subjects[index]
        return None
    
    def get_subject_by_id(self, subject_id: str) -> Optional[SubjectData]:
        """
        Get subject by ID.
        
        Args:
            subject_id: Subject ID to find
            
        Returns:
            SubjectData instance or None if not found
        """
        for subject in self._subjects:
            if subject.subject_id == subject_id:
                return subject
        return None
    
    def get_selected_subject(self) -> Optional[SubjectData]:
        """
        Get currently selected subject.
        
        Returns:
            SubjectData instance or None if no selection
        """
        return self.get_subject(self._selected_subject_index)
    
    def get_subject_ids(self) -> List[str]:
        """
        Get list of all subject IDs.
        
        Returns:
            List of subject ID strings
        """
        return [subject.subject_id for subject in self._subjects]
    
    def get_display_names(self) -> List[str]:
        """
        Get list of display names for UI (original [mapped] format).
        
        Returns:
            List of display name strings
        """
        return [subject.display_name or subject.subject_id for subject in self._subjects]
    
    def count(self) -> int:
        """Get number of subjects."""
        return len(self._subjects)
    
    def is_empty(self) -> bool:
        """Check if model is empty."""
        return len(self._subjects) == 0
    
    def clear(self):
        """Clear all subjects from the model."""
        self._subjects.clear()
        self._selected_subject_index = -1
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about subjects and files.
        
        Returns:
            Dictionary with statistics
        """
        total_files = 0
        modalities = set()
        sessions = set()
        tasks = set()
        
        for subject in self._subjects:
            total_files += subject.get_file_count()
            
            for file_data in subject.files:
                if file_data.get("modality"):
                    modalities.add(file_data["modality"])
                if file_data.get("session"):
                    sessions.add(file_data["session"])
                if file_data.get("task"):
                    tasks.add(file_data["task"])
        
        return {
            "total_subjects": len(self._subjects),
            "total_files": total_files,
            "modalities": list(modalities),
            "sessions": list(sessions),
            "tasks": list(tasks),
            "average_files_per_subject": total_files / len(self._subjects) if self._subjects else 0
        }
    
    def validate_all_subjects(self) -> tuple[bool, List[str]]:
        """
        Validate all subjects and their files.
        
        Returns:
            Tuple of (all_valid, error_messages)
        """
        all_valid = True
        errors = []
        
        for i, subject in enumerate(self._subjects):
            # Validate subject ID
            if not subject.subject_id:
                all_valid = False
                errors.append(f"Subject {i+1}: Missing subject ID")
                continue
            
            # Validate files
            for j, file_data in enumerate(subject.files):
                file_path = file_data.get("file_path", "")
                if not file_path:
                    all_valid = False
                    errors.append(f"Subject {subject.subject_id}, File {j+1}: Missing file path")
                elif not os.path.exists(file_path):
                    all_valid = False
                    errors.append(f"Subject {subject.subject_id}, File {j+1}: File does not exist")
                
                if not file_data.get("modality"):
                    all_valid = False
                    errors.append(f"Subject {subject.subject_id}, File {j+1}: Missing modality")
        
        return all_valid, errors
    
    def prepare_for_import(self) -> List[Dict[str, Any]]:
        """
        Prepare all subjects for import worker.
        
        Returns:
            List of subject dictionaries ready for import
        """
        prepared_subjects = []
        
        for subject in self._subjects:
            # Validate subject before adding to import list
            if subject.subject_id and subject.files:
                prepared_subjects.append(subject.to_dict())
        
        return prepared_subjects
    
    # Backward compatibility methods
    
    def load_from_legacy_format(self, subjects_data: List[Dict[str, Any]]):
        """
        Load subjects from legacy format.
        
        Args:
            subjects_data: List of subject dictionaries in original format
        """
        self.clear()
        
        for subject_dict in subjects_data:
            try:
                subject_data = SubjectData.from_dict(subject_dict)
                self.add_subject(subject_data)
            except ValueError as e:
                logger.warning("Skipping invalid subject data: %s", e)
        
        # Set selection to first subject if available
        if self.count() > 0:
            self.selected_subject_index = 0
    
    def get_legacy_format(self) -> List[Dict[str, Any]]:
        """
        Get subjects in legacy format for backward compatibility.
        
        Returns:
            List of subject dictionaries in original format
        """
        return [subject.to_dict() for subject in self._subjects]
    
    def crawl_and_load_subjects(self, config_path: str, subject_mapping: Dict[str, str] = None):
        """
        Use DataCrawlerService to load subjects.
        
        Args:
            config_path: Path to crawler configuration file
            subject_mapping: Optional dictionary mapping original subject IDs to new names
        """
        from ..services.DataCrawlerService import DataCrawlerService
        
        subjects_data = DataCrawlerService.crawl_and_process_subjects(config_path, subject_mapping)
        self.load_from_legacy_format(subjects_data)
    
    def remove_selected_subjects(self, selected_indices: List[int]) -> int:
        """
        Remove multiple subjects by indices.
        
        Args:
            selected_indices: List of indices to remove (sorted in descending order)
            
        Returns:
            Number of subjects removed
        """
        removed_count = 0
        
        # Sort indices in descending order to avoid index shifting issues
        for index in sorted(selected_indices, reverse=True):
            if self.remove_subject(index):
                removed_count += 1
        
        return removed_count