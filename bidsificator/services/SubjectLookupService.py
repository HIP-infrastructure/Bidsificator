"""Service for handling CSV lookup table functionality for subject name mapping."""

import csv
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, List


class SubjectLookupService:
    """Handles CSV lookup table parsing and subject name mapping."""
    
    @staticmethod
    def parse_lookup_table(csv_path: str) -> Tuple[Dict[str, str], List[str]]:
        """
        Parse CSV lookup table file.
        
        Expected format: FolderID;CenterID;SubjectID
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Tuple of (mapping_dict, error_messages)
            mapping_dict: {original_id: formatted_name}
            error_messages: List of validation errors
        """
        mapping = {}
        errors = []
        
        if not csv_path or not Path(csv_path).exists():
            errors.append("CSV file does not exist")
            return mapping, errors
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                # Try to detect delimiter
                sample = file.read(1024)
                file.seek(0)
                
                delimiter = ';'  # Default
                if sample.count(';') < sample.count(','):
                    delimiter = ','
                
                reader = csv.DictReader(file, delimiter=delimiter)
                
                # Validate headers
                expected_headers = {'FolderID', 'CenterID', 'SubjectID'}
                if not expected_headers.issubset(set(reader.fieldnames or [])):
                    errors.append(f"Invalid headers. Expected: {expected_headers}, Found: {reader.fieldnames}")
                    return mapping, errors
                
                used_names = set()
                line_number = 1  # Header is line 0
                
                for row in reader:
                    line_number += 1
                    
                    folder_id = row.get('FolderID', '').strip()
                    center_id_str = row.get('CenterID', '').strip()
                    subject_id_str = row.get('SubjectID', '').strip()
                    
                    # Validate required fields
                    if not folder_id:
                        errors.append(f"Line {line_number}: Empty FolderID")
                        continue
                    
                    if not center_id_str or not subject_id_str:
                        errors.append(f"Line {line_number}: Missing CenterID or SubjectID for {folder_id}")
                        continue
                    
                    # Check if using CUSTOM mode
                    if center_id_str.upper() == 'CUSTOM':
                        # Custom mode - SubjectID can be alphanumeric
                        if not re.match(r'^[a-zA-Z0-9]+$', subject_id_str):
                            errors.append(f"Line {line_number}: SubjectID must be alphanumeric only, got '{subject_id_str}'")
                            continue
                        # Use subject_id directly as the formatted name
                        formatted_name = subject_id_str
                    else:
                        # Numeric mode - validate and parse numeric IDs
                        try:
                            center_id = int(center_id_str)
                            if center_id < 0 or center_id > 999:
                                errors.append(f"Line {line_number}: CenterID must be 0-999, got {center_id}")
                                continue
                        except ValueError:
                            errors.append(f"Line {line_number}: CenterID must be numeric (0-999) or 'CUSTOM', got '{center_id_str}'"
                            continue
                        
                        try:
                            subject_id = int(subject_id_str)
                            if subject_id < 0 or subject_id > 9999:
                                errors.append(f"Line {line_number}: SubjectID must be 0-9999, got {subject_id}")
                                continue
                        except ValueError:
                            errors.append(f"Line {line_number}: SubjectID must be numeric when CenterID is numeric, got '{subject_id_str}'")
                            continue
                        
                        # Format subject name using numeric format
                        formatted_name = SubjectLookupService.format_subject_name(center_id, subject_id)
                    
                    if not formatted_name:
                        if center_id_str.upper() == 'CUSTOM':
                            errors.append(f"Line {line_number}: Could not create valid subject name from SubjectID='{subject_id_str}'")
                        else:
                            errors.append(f"Line {line_number}: Could not create valid subject name from CenterID={center_id}, SubjectID={subject_id}")
                        continue
                    
                    # Normalize folder_id for case-insensitive matching
                    folder_id_lower = folder_id.lower()
                    
                    # Check for duplicates in CSV (case-insensitive)
                    if any(k.lower() == folder_id_lower for k in mapping.keys()):
                        errors.append(f"Line {line_number}: Duplicate FolderID '{folder_id}' (case-insensitive)")
                        continue
                    
                    # Check for name conflicts
                    if formatted_name in used_names:
                        if center_id_str.upper() == 'CUSTOM':
                            errors.append(f"Line {line_number}: Duplicate subject name '{formatted_name}'")
                        else:
                            errors.append(f"Line {line_number}: Duplicate subject name '{formatted_name}' (from CenterID={center_id}, SubjectID={subject_id})")
                        continue
                    
                    # Store multiple case variations for matching
                    # This allows matching Pat_44, PAT_44, pat_44, etc.
                    mapping[folder_id] = formatted_name
                    mapping[folder_id.lower()] = formatted_name
                    mapping[folder_id.upper()] = formatted_name
                    # Also try with first letter capitalized
                    mapping[folder_id.capitalize()] = formatted_name
                    
                    used_names.add(formatted_name)
                
        except Exception as e:
            errors.append(f"Error reading CSV file: {str(e)}")
        
        return mapping, errors
    
    @staticmethod
    def format_subject_name(center_id: int, subject_id: int) -> str:
        """
        Create BIDS-compatible subject name from numeric center and subject IDs.
        
        Format: ZZZXXXX where:
        - ZZZ: 3-digit center ID (000-999)
        - XXXX: 4-digit subject ID (0000-9999)
        
        Note: For custom alphanumeric IDs, use CUSTOM mode in the CSV.
        
        Args:
            center_id: Center identifier (0-999)
            subject_id: Subject identifier (0-9999)
            
        Returns:
            Formatted subject name (e.g., "0010123")
        """
        # Validate ranges
        if center_id < 0 or center_id > 999:
            return ""
        if subject_id < 0 or subject_id > 9999:
            return ""
        
        # Create fixed-format name: ZZZXXXX (7 digits total)
        formatted_name = f"{center_id:03d}{subject_id:04d}"
        
        return formatted_name
    
    @staticmethod
    def validate_csv_format(csv_path: str) -> Tuple[bool, List[str]]:
        """
        Quick validation of CSV format without full parsing.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not csv_path:
            errors.append("No file path provided")
            return False, errors
        
        csv_file = Path(csv_path)
        if not csv_file.exists():
            errors.append("File does not exist")
            return False, errors
        
        if not csv_file.suffix.lower() in ['.csv', '.txt']:
            errors.append("File must be a .csv or .txt file")
            return False, errors
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                first_line = file.readline().strip()
                
                # Check if it looks like a header
                if not any(delimiter in first_line for delimiter in [';', ',']):
                    errors.append("File does not appear to be properly delimited")
                    return False, errors
                
                # Check for expected headers (case insensitive)
                first_line_lower = first_line.lower()
                required_terms = ['folderid', 'centerid', 'subjectid']
                
                if not all(term in first_line_lower for term in required_terms):
                    errors.append("File does not contain expected headers (FolderID, CenterID, SubjectID)")
                    errors.append("CenterID can be numeric (0-999) or 'CUSTOM' for alphanumeric SubjectIDs")
                    return False, errors
                
        except Exception as e:
            errors.append(f"Error reading file: {str(e)}")
            return False, errors
        
        return True, []
    
    @staticmethod
    def get_mapping_preview(csv_path: str, limit: int = 10) -> Tuple[List[Tuple[str, str]], List[str]]:
        """
        Get a preview of the mapping for UI display.
        
        Args:
            csv_path: Path to CSV file
            limit: Maximum number of mappings to return
            
        Returns:
            Tuple of (preview_list, error_messages)
            preview_list: List of (original_id, mapped_name) tuples
        """
        mapping, errors = SubjectLookupService.parse_lookup_table(csv_path)
        
        if errors:
            return [], errors
        
        # Return first N mappings for preview
        preview = list(mapping.items())[:limit]
        return preview, []
    
    @staticmethod
    def generate_template_csv(subject_ids: List[str] = None) -> str:
        """
        Generate CSV template content for subject lookup table.
        
        Args:
            subject_ids: Optional list of subject IDs to pre-populate
            
        Returns:
            CSV content as string
        """
        # CSV header
        csv_lines = ["FolderID;CenterID;SubjectID"]
        
        if subject_ids:
            # Pre-populate with subject IDs, leaving center/subject fields for manual entry
            for i, subject_id in enumerate(subject_ids):
                # Generate sequential IDs with center 000
                subject_num = str(i + 1).zfill(4)  # 0001, 0002, etc.
                csv_lines.append(f"{subject_id};000;{subject_num}")
        else:
            # Add example rows showing both modes
            csv_lines.extend([
                "# Numeric mode examples (CenterID is numeric 0-999):",
                "PAT_001;001;0123",  # Will become 0010123
                "PAT_002;013;0456",  # Will become 0130456
                "PAT_003;239;0789",  # Will become 2390789
                "",
                "# Custom mode examples (CenterID is 'CUSTOM'):",
                "PAT_004;CUSTOM;CHUV001",   # Will become CHUV001
                "PAT_005;CUSTOM;patient123",  # Will become patient123
                "PAT_006;CUSTOM;JohnDoe",     # Will become JohnDoe
            ])
        
        return "\n".join(csv_lines)
    
    @staticmethod
    def save_template_to_file(csv_content: str, file_path: str) -> Tuple[bool, str]:
        """
        Save CSV template content to file.
        
        Args:
            csv_content: CSV content to save
            file_path: Path where to save the file
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            with open(file_path, 'w', encoding='utf-8', newline='') as file:
                file.write(csv_content)
            return True, ""
        except PermissionError:
            return False, f"Permission denied: Cannot write to {file_path}"
        except OSError as e:
            return False, f"File system error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    @staticmethod
    def create_template_file(file_path: str, subject_ids: List[str] = None) -> Tuple[bool, str]:
        """
        Create a complete lookup table template file.
        
        Args:
            file_path: Path where to save the template
            subject_ids: Optional list of subject IDs to pre-populate
            
        Returns:
            Tuple of (success, error_message)
        """
        # Generate CSV content
        csv_content = SubjectLookupService.generate_template_csv(subject_ids)
        
        # Save to file
        return SubjectLookupService.save_template_to_file(csv_content, file_path)