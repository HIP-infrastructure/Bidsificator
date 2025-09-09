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
        
        Expected format: FolderID;CenterName;NumericID
        
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
                expected_headers = {'FolderID', 'CenterName', 'NumericID'}
                if not expected_headers.issubset(set(reader.fieldnames or [])):
                    errors.append(f"Invalid headers. Expected: {expected_headers}, Found: {reader.fieldnames}")
                    return mapping, errors
                
                used_names = set()
                line_number = 1  # Header is line 0
                
                for row in reader:
                    line_number += 1
                    
                    folder_id = row.get('FolderID', '').strip()
                    center_name = row.get('CenterName', '').strip()
                    numeric_id = row.get('NumericID', '').strip()
                    
                    # Validate required fields
                    if not folder_id:
                        errors.append(f"Line {line_number}: Empty FolderID")
                        continue
                    
                    if not center_name or not numeric_id:
                        errors.append(f"Line {line_number}: Missing CenterName or NumericID for {folder_id}")
                        continue
                    
                    # Format subject name
                    formatted_name = SubjectLookupService.format_subject_name(center_name, numeric_id)
                    
                    if not formatted_name:
                        errors.append(f"Line {line_number}: Could not create valid subject name from '{center_name}' '{numeric_id}'")
                        continue
                    
                    # Normalize folder_id for case-insensitive matching
                    folder_id_lower = folder_id.lower()
                    
                    # Check for duplicates in CSV (case-insensitive)
                    if any(k.lower() == folder_id_lower for k in mapping.keys()):
                        errors.append(f"Line {line_number}: Duplicate FolderID '{folder_id}' (case-insensitive)")
                        continue
                    
                    # Check for name conflicts
                    if formatted_name in used_names:
                        errors.append(f"Line {line_number}: Duplicate subject name '{formatted_name}' (from '{center_name}' '{numeric_id}')")
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
    def format_subject_name(center_name: str, numeric_id: str) -> str:
        """
        Create anonymous BIDS-compatible subject name from center and numeric ID.
        
        Args:
            center_name: Medical center name
            numeric_id: Anonymous numeric identifier
            
        Returns:
            Formatted subject name (e.g., "Paris_001")
        """
        if not center_name or not numeric_id:
            return ""
        
        # Clean and format center name and numeric ID
        clean_center = SubjectLookupService._clean_center_name(center_name)
        clean_numeric = SubjectLookupService._clean_numeric_id(numeric_id)
        
        if not clean_center or not clean_numeric:
            return ""
        
        # Create anonymous formatted name
        formatted_name = f"{clean_center}_{clean_numeric}"
        
        return formatted_name
    
    @staticmethod
    def _clean_center_name(center_name: str) -> str:
        """
        Clean center name for BIDS compatibility.
        
        Args:
            center_name: Medical center name
            
        Returns:
            Cleaned center name (max 8 chars, alphanumeric and hyphens)
        """
        if not center_name:
            return ""
        
        # Remove special characters, keep only alphanumeric and hyphens
        cleaned = re.sub(r'[^a-zA-Z0-9-]', '', center_name.strip())
        
        # Capitalize and limit length
        if cleaned:
            cleaned = cleaned[:8].upper()  # "LAUSANNE", "LYON", etc.
        
        return cleaned
    
    @staticmethod
    def _clean_numeric_id(numeric_id: str) -> str:
        """
        Clean and format numeric ID.
        
        Args:
            numeric_id: Raw numeric identifier
            
        Returns:
            Cleaned numeric ID (padded to at least 3 digits)
        """
        if not numeric_id:
            return ""
        
        # Extract digits only
        digits = re.sub(r'[^0-9]', '', numeric_id.strip())
        
        if not digits:
            return ""
        
        # Convert to int and back to remove leading zeros, then pad appropriately
        try:
            num = int(digits)
            if num < 1 or num > 99999:  # Support up to 5-digit IDs
                return ""
            # Pad to at least 3 digits, but keep more if needed
            return str(num).zfill(3 if num < 1000 else len(str(num)))
        except ValueError:
            return ""
    
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
                required_terms = ['folderid', 'centername', 'numericid']
                
                if not all(term in first_line_lower for term in required_terms):
                    errors.append("File does not contain expected headers (FolderID, CenterName, NumericID)")
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
        Generate CSV template content for anonymous lookup table.
        
        Args:
            subject_ids: Optional list of subject IDs to pre-populate
            
        Returns:
            CSV content as string
        """
        # CSV header
        csv_lines = ["FolderID;CenterName;NumericID"]
        
        if subject_ids:
            # Pre-populate with subject IDs, leaving center/numeric fields for manual entry
            for i, subject_id in enumerate(subject_ids):
                numeric_id = str(i + 1).zfill(3)  # Generate sequential IDs: 001, 002, etc.
                csv_lines.append(f"{subject_id};CENTER_NAME;{numeric_id}")
        else:
            # Add example rows with realistic anonymous data
            csv_lines.extend([
                "PAT_001;CHUV;001",
                "PAT_002;HCL;002", 
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