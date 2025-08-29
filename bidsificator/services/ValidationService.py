"""Service for BIDS validation operations."""

import os
from typing import List, Tuple, Optional, Dict, Any
from bids_validator import BIDSValidator


class ValidationService:
    """Handles BIDS dataset and file validation."""
    
    @classmethod
    def validate_bids_dataset(cls, dataset_path: str, subject_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate BIDS dataset or specific subject.
        
        Args:
            dataset_path: Path to the BIDS dataset root
            subject_name: Optional subject name to validate (without leading slash)
                         If None, validates entire dataset
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not os.path.exists(dataset_path):
            return False, "Dataset path does not exist"
            
        validator = BIDSValidator()
        
        if subject_name:
            # Validate specific subject
            subject_path = os.path.join(dataset_path, subject_name)
            if not os.path.exists(subject_path):
                return False, f"Subject {subject_name} does not exist"
                
            # Get all files for the subject (excluding hidden files)
            subject_files = []
            for dp, dn, filenames in os.walk(subject_path):
                for f in filenames:
                    if not f.startswith("."):
                        full_path = os.path.join(dp, f)
                        # Convert to relative path from dataset root
                        relative_path = full_path.replace(dataset_path, "")
                        subject_files.append(relative_path)
            
            # Validate all subject files
            all_valid = True
            for file_path in subject_files:
                if not validator.is_bids(file_path):
                    all_valid = False
                    break
            
            if all_valid:
                return True, f"{subject_name} is BIDS compliant"
            else:
                return False, f"{subject_name} is not BIDS compliant"
        else:
            # Validate entire dataset
            # This would require implementing full dataset validation
            # For now, return a basic check
            required_files = ["dataset_description.json"]
            for req_file in required_files:
                if not os.path.exists(os.path.join(dataset_path, req_file)):
                    return False, f"Missing required file: {req_file}"
            
            return True, "Dataset appears to be valid"
    
    @classmethod
    def validate_subject_name(cls, subject_name: str) -> Tuple[bool, str]:
        """
        Validate a BIDS subject name format.
        
        Args:
            subject_name: Subject name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not subject_name:
            return False, "Subject name cannot be empty"
            
        if not subject_name.startswith("sub-"):
            return False, "Subject name should start with 'sub-'"
            
        # Check for valid characters (BIDS allows alphanumeric and limited special chars)
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if not all(c in valid_chars for c in subject_name):
            return False, "Subject name contains invalid characters"
            
        return True, ""
    
    @classmethod
    def validate_session_name(cls, session_name: str) -> Tuple[bool, str]:
        """
        Validate a BIDS session name format.
        
        Args:
            session_name: Session name to validate (can be with or without "ses-" prefix)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not session_name:
            return True, ""  # Session is optional
            
        # Remove ses- prefix if present for validation
        clean_session = session_name
        if session_name.startswith("ses-"):
            clean_session = session_name[4:]
            
        if not clean_session:
            return False, "Session name cannot be empty after 'ses-' prefix"
            
        # Check for valid characters
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if not all(c in valid_chars for c in clean_session):
            return False, "Session name contains invalid characters"
            
        return True, ""
    
    @classmethod
    def validate_task_name(cls, task_name: str) -> Tuple[bool, str]:
        """
        Validate a BIDS task name format.
        
        Args:
            task_name: Task name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not task_name:
            return True, ""  # Task is optional for some modalities
            
        # Check for valid characters
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if not all(c in valid_chars for c in task_name):
            return False, "Task name contains invalid characters"
            
        return True, ""
    
    @classmethod
    def validate_acquisition_name(cls, acquisition_name: str) -> Tuple[bool, str]:
        """
        Validate a BIDS acquisition name format.
        
        Args:
            acquisition_name: Acquisition name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not acquisition_name:
            return True, ""  # Acquisition is optional
            
        # Check for valid characters (typically alphanumeric)
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        if not all(c in valid_chars for c in acquisition_name):
            return False, "Acquisition name should contain only alphanumeric characters"
            
        return True, ""
    
    @classmethod
    def get_validation_summary(cls, dataset_path: str) -> Dict[str, Any]:
        """
        Get a comprehensive validation summary for the dataset.
        
        Args:
            dataset_path: Path to the BIDS dataset root
            
        Returns:
            Dictionary containing validation results
        """
        summary = {
            "dataset_valid": False,
            "required_files_present": [],
            "missing_files": [],
            "subjects": {},
            "total_subjects": 0,
            "valid_subjects": 0
        }
        
        # Check required files
        required_files = ["dataset_description.json", "participants.tsv"]
        for req_file in required_files:
            file_path = os.path.join(dataset_path, req_file)
            if os.path.exists(file_path):
                summary["required_files_present"].append(req_file)
            else:
                summary["missing_files"].append(req_file)
        
        # Check subjects
        try:
            subjects = [f for f in os.listdir(dataset_path) 
                       if os.path.isdir(os.path.join(dataset_path, f)) 
                       and f.startswith("sub-") and not f.startswith(".")]
            
            summary["total_subjects"] = len(subjects)
            
            for subject in subjects:
                is_valid, message = cls.validate_bids_dataset(dataset_path, subject)
                summary["subjects"][subject] = {
                    "valid": is_valid,
                    "message": message
                }
                if is_valid:
                    summary["valid_subjects"] += 1
                    
        except Exception as e:
            summary["error"] = str(e)
        
        summary["dataset_valid"] = (len(summary["missing_files"]) == 0 and 
                                   summary["total_subjects"] > 0)
        
        return summary