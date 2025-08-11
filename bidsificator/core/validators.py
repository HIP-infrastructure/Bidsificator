"""Validators for various data types used throughout the application."""

import re
from typing import List, Optional


class FileExtensionValidator:
    """Validates file extension formats."""
    
    @staticmethod
    def is_valid_extensions(input_string: str) -> bool:
        """
        Validate a comma-separated string of file extensions.
        
        Args:
            input_string: String containing file extensions separated by ", "
            
        Returns:
            bool: True if valid format, False otherwise
            
        Examples:
            ".txt" -> True
            ".txt, .pdf" -> True
            ".tar.gz, .zip" -> True
            "txt" -> False (missing dot)
            ".txt,.pdf" -> False (missing space after comma)
        """
        if not input_string:
            return False
            
        # Regular expression to match valid file extensions separated by ", "
        pattern = r'^(\.[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)?)(, \.[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)?)*$'
        return bool(re.match(pattern, input_string))
    
    @staticmethod
    def parse_extensions(input_string: str) -> List[str]:
        """
        Parse a comma-separated string of file extensions into a list.
        
        Args:
            input_string: String containing file extensions separated by ", "
            
        Returns:
            List of extension strings, or empty list if invalid
        """
        if not FileExtensionValidator.is_valid_extensions(input_string):
            return []
        return input_string.split(', ')
    
    @staticmethod
    def format_extensions(extensions: List[str]) -> str:
        """
        Format a list of extensions into a comma-separated string.
        
        Args:
            extensions: List of file extension strings
            
        Returns:
            Formatted string with extensions separated by ", "
        """
        return ', '.join(extensions)


class SubjectPatternValidator:
    """Validates BIDS subject pattern formats."""
    
    @staticmethod
    def is_valid_pattern(pattern: str) -> bool:
        """
        Validate a subject pattern string.
        
        Args:
            pattern: Subject pattern string (e.g., '*_*_*')
            
        Returns:
            bool: True if pattern is non-empty
        """
        return bool(pattern and pattern.strip())