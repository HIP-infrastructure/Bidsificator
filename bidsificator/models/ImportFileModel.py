"""Model for managing individual import file data and operations."""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImportFileData:
    """Data structure for a single import file."""
    file_name: str
    file_path: str
    modality: str
    task: str = ""
    session: str = ""
    contrast_agent: str = ""
    acquisition: str = ""
    reconstruction: str = ""
    intended_subject: str = ""
    
    def __post_init__(self):
        """Validate and clean data after initialization."""
        # Ensure file_name matches file_path
        if self.file_path and not self.file_name:
            self.file_name = os.path.basename(self.file_path)
        
        # Clean session prefix if present
        if self.session.startswith("ses-"):
            self.session = self.session[4:]
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format (for backward compatibility)."""
        return {
            "file_name": self.file_name,
            "file_path": self.file_path,
            "modality": self.modality,
            "task": self.task,
            "session": self.session,
            "contrast_agent": self.contrast_agent,
            "acquisition": self.acquisition,
            "reconstruction": self.reconstruction,
            "intended_subject": self.intended_subject
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImportFileData':
        """Create from dictionary format (for backward compatibility)."""
        return cls(
            file_name=data.get("file_name", ""),
            file_path=data.get("file_path", ""),
            modality=data.get("modality", ""),
            task=data.get("task", ""),
            session=data.get("session", ""),
            contrast_agent=data.get("contrast_agent", ""),
            acquisition=data.get("acquisition", ""),
            reconstruction=data.get("reconstruction", ""),
            intended_subject=data.get("intended_subject", "")
        )
    
    def validate(self) -> tuple[bool, str]:
        """Validate the file data."""
        if not self.file_name:
            return False, "File name is required"
        if not self.file_path:
            return False, "File path is required"
        if not self.modality:
            return False, "Modality is required"
        if not os.path.exists(self.file_path):
            return False, f"File does not exist: {self.file_path}"
        return True, ""
    
    def get_session_with_prefix(self) -> str:
        """Get session with 'ses-' prefix if session exists."""
        return f"ses-{self.session}" if self.session else ""


class ImportFileModel:
    """Model for managing import file data and operations."""
    
    def __init__(self):
        """Initialize empty import file model."""
        self._files: List[ImportFileData] = []
        self._current_subject: str = ""
    
    @property
    def files(self) -> List[ImportFileData]:
        """Get list of import files."""
        return self._files.copy()
    
    @property
    def current_subject(self) -> str:
        """Get current subject ID."""
        return self._current_subject
    
    @current_subject.setter
    def current_subject(self, subject_id: str):
        """Set current subject ID."""
        self._current_subject = subject_id
    
    def add_file(self, file_data: ImportFileData) -> bool:
        """
        Add a file to the import list.
        
        Args:
            file_data: ImportFileData instance to add
            
        Returns:
            True if added successfully, False if duplicate
        """
        # Check for duplicates
        if self.has_file(file_data.file_path):
            return False
        
        # Set intended subject if not already set
        if not file_data.intended_subject:
            file_data.intended_subject = self._current_subject
            
        self._files.append(file_data)
        return True
    
    def remove_file(self, index: int) -> bool:
        """
        Remove a file by index.
        
        Args:
            index: Index of file to remove
            
        Returns:
            True if removed successfully, False if index invalid
        """
        if 0 <= index < len(self._files):
            self._files.pop(index)
            return True
        return False
    
    def remove_file_by_path(self, file_path: str) -> bool:
        """
        Remove a file by path.
        
        Args:
            file_path: Path of file to remove
            
        Returns:
            True if removed successfully, False if not found
        """
        for i, file_data in enumerate(self._files):
            if file_data.file_path == file_path:
                self._files.pop(i)
                return True
        return False
    
    def has_file(self, file_path: str) -> bool:
        """
        Check if a file path already exists in the list.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        return any(file_data.file_path == file_path for file_data in self._files)
    
    def get_file(self, index: int) -> Optional[ImportFileData]:
        """
        Get file data by index.
        
        Args:
            index: Index of file to get
            
        Returns:
            ImportFileData instance or None if index invalid
        """
        if 0 <= index < len(self._files):
            return self._files[index]
        return None
    
    def update_file(self, index: int, file_data: ImportFileData) -> bool:
        """
        Update file data at index.
        
        Args:
            index: Index of file to update
            file_data: New file data
            
        Returns:
            True if updated successfully, False if index invalid
        """
        if 0 <= index < len(self._files):
            self._files[index] = file_data
            return True
        return False
    
    def update_all_subjects(self, new_subject: str):
        """
        Update all files to use a new subject ID.
        
        Args:
            new_subject: New subject ID to apply to all files
        """
        self._current_subject = new_subject
        for file_data in self._files:
            file_data.intended_subject = new_subject
    
    def clear(self):
        """Clear all files from the model."""
        self._files.clear()
        self._current_subject = ""
    
    def count(self) -> int:
        """Get number of files in the model."""
        return len(self._files)
    
    def is_empty(self) -> bool:
        """Check if the model is empty."""
        return len(self._files) == 0
    
    def get_files_as_dicts(self) -> List[Dict[str, str]]:
        """
        Get files as list of dictionaries (for backward compatibility).
        
        Returns:
            List of file dictionaries
        """
        return [file_data.to_dict() for file_data in self._files]
    
    def load_from_dicts(self, files_data: List[Dict[str, Any]], subject_id: str = ""):
        """
        Load files from list of dictionaries (for backward compatibility).
        
        Args:
            files_data: List of file dictionaries
            subject_id: Subject ID to set
        """
        self.clear()
        self._current_subject = subject_id
        
        for file_dict in files_data:
            file_data = ImportFileData.from_dict(file_dict)
            if not file_data.intended_subject:
                file_data.intended_subject = subject_id
            self._files.append(file_data)
    
    def validate_all(self) -> tuple[bool, List[str]]:
        """
        Validate all files in the model.
        
        Returns:
            Tuple of (all_valid, error_messages)
        """
        all_valid = True
        errors = []
        
        for i, file_data in enumerate(self._files):
            is_valid, error = file_data.validate()
            if not is_valid:
                all_valid = False
                errors.append(f"File {i+1}: {error}")
        
        return all_valid, errors
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the files.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_files": len(self._files),
            "modalities": {},
            "sessions": set(),
            "tasks": set(),
            "subjects": set()
        }
        
        for file_data in self._files:
            # Count modalities
            modality = file_data.modality
            stats["modalities"][modality] = stats["modalities"].get(modality, 0) + 1
            
            # Collect unique values
            if file_data.session:
                stats["sessions"].add(file_data.session)
            if file_data.task:
                stats["tasks"].add(file_data.task)
            if file_data.intended_subject:
                stats["subjects"].add(file_data.intended_subject)
        
        # Convert sets to lists for JSON serialization
        stats["sessions"] = list(stats["sessions"])
        stats["tasks"] = list(stats["tasks"])
        stats["subjects"] = list(stats["subjects"])
        
        return stats