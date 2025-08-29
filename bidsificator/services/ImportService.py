"""Service for coordinating file and subject import operations."""

import os
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from .FileDetectionService import FileDetectionService


class ImportService:
    """Handles the coordination of file and subject import operations."""
    
    @classmethod
    def get_next_acquisition_number(cls, existing_files: List[Dict], 
                                   session: str, modality: str, task: str) -> str:
        """
        Auto-increment acquisition for files with same properties.
        
        Args:
            existing_files: List of existing file data dictionaries
            session: Session identifier
            modality: File modality
            task: Task identifier
            
        Returns:
            Next acquisition number as zero-padded string (e.g., "01", "02")
        """
        # Find existing files with same properties
        existing_acquisitions = []
        for file_data in existing_files:
            if (file_data.get("session") == session and
                file_data.get("modality") == modality and 
                file_data.get("task") == task):
                # Extract acquisition number (01, 02, 03 format)
                acq = file_data.get("acquisition", "")
                if acq:
                    try:
                        existing_acquisitions.append(int(acq))
                    except ValueError:
                        pass
        
        # Find next available number
        next_num = max(existing_acquisitions, default=0) + 1
        return f"{next_num:02d}"
    
    @classmethod
    def create_file_data_from_form(cls, file_path: str, form_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Create a file data structure from form inputs.
        
        Args:
            file_path: Path to the file
            form_data: Dictionary containing form field values
                      Expected keys: modality, session, task, contrast_agent, 
                                   acquisition, reconstruction
                      
        Returns:
            Dictionary containing complete file data
        """
        file_name = os.path.basename(file_path)
        
        # Extract session without "ses-" prefix for storage
        session = form_data.get("session", "")
        if session.startswith("ses-"):
            session = session[4:]
        
        return {
            "file_name": file_name,
            "file_path": file_path,
            "modality": form_data.get("modality", ""),
            "task": form_data.get("task", ""),
            "session": session,
            "contrast_agent": form_data.get("contrast_agent", ""),
            "acquisition": form_data.get("acquisition", ""),
            "reconstruction": form_data.get("reconstruction", "")
        }
    
    @classmethod
    def process_multiple_files(cls, file_paths: List[str], 
                              form_defaults: Dict[str, str], 
                              existing_files: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        Process multiple files for batch import.
        
        Args:
            file_paths: List of file paths to process
            form_defaults: Default values from form fields
            existing_files: List of existing file data to check for duplicates
            
        Returns:
            Tuple of (successful_files, failed_files)
            successful_files: List of file data dictionaries
            failed_files: List of error messages for failed files
        """
        successful_files = []
        failed_files = []
        
        for file_path in file_paths:
            try:
                # Auto-detect modality
                detected_modality = FileDetectionService.detect_modality_from_file(file_path)
                if not detected_modality:
                    failed_files.append(f"{os.path.basename(file_path)}: Unsupported file type")
                    continue
                
                # Determine task based on modality
                if "(anat)" in detected_modality or "photo" in detected_modality:
                    task = ""  # Anatomy and photos don't use tasks
                else:
                    task = form_defaults.get("task", "")
                
                # Extract session without prefix for acquisition calculation
                session = form_defaults.get("session", "")
                if session.startswith("ses-"):
                    session = session[4:]
                
                # Auto-increment acquisition if needed
                acquisition = cls.get_next_acquisition_number(
                    successful_files + existing_files,  # Include both new and existing
                    session,
                    detected_modality,
                    task
                )
                
                # Create file entry
                file_data = {
                    "file_name": os.path.basename(file_path),
                    "file_path": file_path,
                    "modality": detected_modality,
                    "task": task,
                    "session": session,
                    "contrast_agent": form_defaults.get("contrast_agent", "") if "(anat)" in detected_modality else "",
                    "acquisition": acquisition,
                    "reconstruction": form_defaults.get("reconstruction", "") if "(anat)" in detected_modality else ""
                }
                
                # Check for duplicates against existing files
                if not cls._is_duplicate_file(file_data, existing_files):
                    successful_files.append(file_data)
                else:
                    failed_files.append(f"{os.path.basename(file_path)}: File already exists in list")
                    
            except Exception as e:
                failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")
        
        return successful_files, failed_files
    
    @classmethod
    def _is_duplicate_file(cls, file_data: Dict, existing_files: List[Dict]) -> bool:
        """
        Check if a file is already in the existing files list.
        
        Args:
            file_data: File data dictionary to check
            existing_files: List of existing file data dictionaries
            
        Returns:
            True if duplicate found, False otherwise
        """
        file_path = file_data["file_path"]
        for existing_file in existing_files:
            if existing_file["file_path"] == file_path:
                return True
        return False
    
    @classmethod 
    def validate_file_data(cls, file_data: Dict) -> Tuple[bool, str]:
        """
        Validate a file data structure.
        
        Args:
            file_data: File data dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["file_name", "file_path", "modality"]
        
        for field in required_fields:
            if not file_data.get(field):
                return False, f"Missing required field: {field}"
        
        # Check if file exists
        if not os.path.exists(file_data["file_path"]):
            return False, f"File does not exist: {file_data['file_path']}"
            
        return True, ""
    
    @classmethod
    def prepare_subject_for_import(cls, subject_id: str, files: List[Dict]) -> Dict[str, Any]:
        """
        Prepare a subject data structure for import worker.
        
        Args:
            subject_id: Subject identifier
            files: List of file data dictionaries
            
        Returns:
            Subject data dictionary ready for import worker
        """
        # Validate all files
        valid_files = []
        for file_data in files:
            is_valid, error = cls.validate_file_data(file_data)
            if is_valid:
                valid_files.append(file_data)
            else:
                print(f"Warning: Skipping invalid file: {error}")
        
        return {
            "subject_id": subject_id,
            "files": valid_files
        }