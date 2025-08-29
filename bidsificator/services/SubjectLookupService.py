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
        
        Expected format: MicromedID;Surname;Firstname
        
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
                expected_headers = {'MicromedID', 'Surname', 'Firstname'}
                if not expected_headers.issubset(set(reader.fieldnames or [])):
                    errors.append(f"Invalid headers. Expected: {expected_headers}, Found: {reader.fieldnames}")
                    return mapping, errors
                
                used_names = set()
                line_number = 1  # Header is line 0
                
                for row in reader:
                    line_number += 1
                    
                    micromed_id = row.get('MicromedID', '').strip()
                    surname = row.get('Surname', '').strip()
                    firstname = row.get('Firstname', '').strip()
                    
                    # Validate required fields
                    if not micromed_id:
                        errors.append(f"Line {line_number}: Empty MicromedID")
                        continue
                    
                    if not surname or not firstname:
                        errors.append(f"Line {line_number}: Missing surname or firstname for {micromed_id}")
                        continue
                    
                    # Format subject name
                    formatted_name = SubjectLookupService.format_subject_name(surname, firstname)
                    
                    if not formatted_name:
                        errors.append(f"Line {line_number}: Could not create valid subject name from '{surname}' '{firstname}'")
                        continue
                    
                    # Check for duplicates in CSV
                    if micromed_id in mapping:
                        errors.append(f"Line {line_number}: Duplicate MicromedID '{micromed_id}'")
                        continue
                    
                    # Check for name conflicts
                    if formatted_name in used_names:
                        errors.append(f"Line {line_number}: Duplicate subject name '{formatted_name}' (from '{surname}' '{firstname}')")
                        continue
                    
                    mapping[micromed_id] = formatted_name
                    used_names.add(formatted_name)
                
        except Exception as e:
            errors.append(f"Error reading CSV file: {str(e)}")
        
        return mapping, errors
    
    @staticmethod
    def format_subject_name(surname: str, firstname: str) -> str:
        """
        Create BIDS-compatible subject name from surname and firstname.
        
        Args:
            surname: Subject's surname
            firstname: Subject's firstname
            
        Returns:
            Formatted subject name (e.g., "John_Doe")
        """
        if not surname or not firstname:
            return ""
        
        # Clean and format names
        clean_surname = SubjectLookupService._clean_name(surname)
        clean_firstname = SubjectLookupService._clean_name(firstname)
        
        if not clean_surname or not clean_firstname:
            return ""
        
        # Create formatted name
        formatted_name = f"{clean_firstname}_{clean_surname}"
        
        # Ensure BIDS compliance (alphanumeric + underscore, max reasonable length)
        if len(formatted_name) > 50:  # Reasonable limit
            # Truncate while preserving both names
            max_part = 24  # Allow for underscore
            clean_firstname = clean_firstname[:max_part]
            clean_surname = clean_surname[:max_part]
            formatted_name = f"{clean_firstname}_{clean_surname}"
        
        return formatted_name
    
    @staticmethod
    def _clean_name(name: str) -> str:
        """
        Clean name for BIDS compatibility.
        
        Args:
            name: Raw name string
            
        Returns:
            Cleaned name (alphanumeric only)
        """
        if not name:
            return ""
        
        # Remove accents and special characters, keep only alphanumeric
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', name.strip())
        
        # Capitalize first letter
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:].lower()
        
        return cleaned
    
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
                required_terms = ['micromed', 'surname', 'firstname']
                
                if not all(term in first_line_lower for term in required_terms):
                    errors.append("File does not contain expected headers (MicromedID, Surname, Firstname)")
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
        Generate CSV template content for lookup table.
        
        Args:
            subject_ids: Optional list of subject IDs to pre-populate
            
        Returns:
            CSV content as string
        """
        # CSV header
        csv_lines = ["MicromedID;Surname;Firstname"]
        
        if subject_ids:
            # Pre-populate with subject IDs, leaving name fields empty
            for subject_id in subject_ids:
                csv_lines.append(f"{subject_id};;")
        else:
            # Just add a few example rows for manual entry
            csv_lines.extend([
                "PAT_001;;",
                "PAT_002;;",
                "PAT_003;;"
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