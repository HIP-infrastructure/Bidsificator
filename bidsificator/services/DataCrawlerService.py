"""Service for data crawling and subject parsing operations."""

from typing import List, Dict, Any
from pathlib import Path

from ..core.DataCrawler import DataCrawler


class DataCrawlerService:
    """Handles data crawling operations and subject data processing."""
    
    @classmethod
    def crawl_and_process_subjects(cls, config_path: str) -> List[Dict[str, Any]]:
        """
        Crawl data using configuration and process into subject format.
        
        Args:
            config_path: Path to the configuration YAML file
            
        Returns:
            List of subject dictionaries with processed file data
        """
        # Use existing DataCrawler to get raw data
        raw_subject_data = DataCrawler.crawl_data(config_path)
        
        processed_subjects = []
        for subject in raw_subject_data:
            processed_subject = cls._process_subject_data(subject)
            processed_subjects.append(processed_subject)
            
        return processed_subjects
    
    @classmethod
    def _process_subject_data(cls, subject: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw subject data into the expected format.
        
        Args:
            subject: Raw subject data from DataCrawler
            
        Returns:
            Processed subject data with files list
        """
        files = []
        acquisition_tracker = {}  # Track acquisitions per modality/session/task combo
        
        # Process data types into individual files
        for data_type, data_info in subject["data"].items():
            for file_path in data_info["file_paths"]:
                file_name = Path(file_path).name
                modality = data_info['modality']
                session = "post"  # Default session from original logic
                task = ""  # Default empty task
                
                # Auto-increment acquisition for files with same properties
                key = f"{modality}_{session}_{task}"
                if key not in acquisition_tracker:
                    acquisition_tracker[key] = 0
                acquisition_tracker[key] += 1
                acquisition = f"{acquisition_tracker[key]:02d}"
                
                file_data = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "modality": modality,
                    "task": task,
                    "session": session,
                    "contrast_agent": "",
                    "acquisition": acquisition,
                    "reconstruction": ""
                }
                files.append(file_data)
        
        # Create processed subject
        processed_subject = {
            "subject_id": subject["subject_id"],
            "files": files
        }
        
        return processed_subject
    
    @classmethod
    def get_subject_by_id(cls, subjects: List[Dict], subject_id: str) -> Dict[str, Any]:
        """
        Find a subject by ID from a list of subjects.
        
        Args:
            subjects: List of subject dictionaries
            subject_id: Subject ID to find
            
        Returns:
            Subject dictionary or empty dict if not found
        """
        for subject in subjects:
            if subject.get("subject_id") == subject_id:
                return subject
        return {}
    
    @classmethod
    def remove_subject_by_id(cls, subjects: List[Dict], subject_id: str) -> bool:
        """
        Remove a subject by ID from a list of subjects.
        
        Args:
            subjects: List of subject dictionaries to modify
            subject_id: Subject ID to remove
            
        Returns:
            True if subject was found and removed, False otherwise
        """
        for i, subject in enumerate(subjects):
            if subject.get("subject_id") == subject_id:
                subjects.pop(i)
                return True
        return False
    
    @classmethod
    def get_subject_statistics(cls, subjects: List[Dict]) -> Dict[str, Any]:
        """
        Get statistics about the subjects and their files.
        
        Args:
            subjects: List of subject dictionaries
            
        Returns:
            Dictionary containing statistics
        """
        stats = {
            "total_subjects": len(subjects),
            "total_files": 0,
            "modalities": set(),
            "sessions": set(),
            "tasks": set()
        }
        
        for subject in subjects:
            files = subject.get("files", [])
            stats["total_files"] += len(files)
            
            for file_data in files:
                if file_data.get("modality"):
                    stats["modalities"].add(file_data["modality"])
                if file_data.get("session"):
                    stats["sessions"].add(file_data["session"])
                if file_data.get("task"):
                    stats["tasks"].add(file_data["task"])
        
        # Convert sets to lists for JSON serialization
        stats["modalities"] = list(stats["modalities"])
        stats["sessions"] = list(stats["sessions"])
        stats["tasks"] = list(stats["tasks"])
        
        return stats