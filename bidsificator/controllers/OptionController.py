"""Controller for managing options/configuration business logic."""

from typing import Dict, List, Optional
from ..core.OptionFile import OptionFile
from ..core.validators import FileExtensionValidator, SubjectPatternValidator


class OptionController:
    """
    Controller that manages the business logic for options/configuration.
    Serves as an intermediary between the OptionWindow (View) and OptionFile (Model).
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the controller with a configuration file path.
        
        Args:
            config_path: Path to the configuration YAML file.
                        If None, uses default path.
        """
        self.config_path = config_path or 'bidsificator/config/config.yaml'
        self.model = OptionFile(self.config_path)
    
    # Database path management
    
    def get_anatomical_db_path(self) -> str:
        """Get the anatomical database path."""
        return self.model.data_paths.get('anatomical', self.model.data_paths.get('main', ''))
    
    def get_functional_db_path(self) -> str:
        """Get the functional database path."""
        return self.model.data_paths.get('functional', self.model.data_paths.get('main', ''))
    
    def set_anatomical_db_path(self, path: str) -> bool:
        """
        Set the anatomical database path.
        
        Args:
            path: The new database path
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not path or not path.strip():
            return False
        
        # Handle both single and dual database setups
        if 'main' in self.model.data_paths:
            self.model.data_paths['main'] = path
        else:
            self.model.data_paths['anatomical'] = path
            # If not using separated databases, update functional too
            if not self.are_databases_separated():
                self.model.data_paths['functional'] = path
            
        return True
    
    def set_functional_db_path(self, path: str) -> bool:
        """
        Set the functional database path.
        
        Args:
            path: The new database path
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not path or not path.strip():
            return False
        
        # Convert to dual database setup if needed
        if 'main' in self.model.data_paths:
            # Convert from single to dual database
            main_path = self.model.data_paths.pop('main')
            self.model.data_paths['anatomical'] = main_path
            self.model.data_paths['functional'] = path
        else:
            self.model.data_paths['functional'] = path
        return True
    
    def are_databases_separated(self) -> bool:
        """Check if anatomical and functional databases are separated."""
        if 'main' in self.model.data_paths:
            return False  # Single database setup
        return self.model.data_paths.get('anatomical', '') != self.model.data_paths.get('functional', '')
    
    def set_databases_separated(self, separated: bool):
        """
        Set whether databases should be separated.
        
        Args:
            separated: True to use separate databases, False to use same
        """
        if not separated:
            # Convert to single database setup
            anat_path = self.get_anatomical_db_path()
            if 'anatomical' in self.model.data_paths:
                # Convert from dual to single
                self.model.data_paths.clear()
                self.model.data_paths['main'] = anat_path
    
    # Subject pattern management
    
    def get_subject_pattern(self) -> str:
        """Get the subject pattern."""
        return self.model.subject_pattern
    
    def set_subject_pattern(self, pattern: str) -> bool:
        """
        Set the subject pattern.
        
        Args:
            pattern: The new subject pattern
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not SubjectPatternValidator.is_valid_pattern(pattern):
            return False
            
        self.model.subject_pattern = pattern
        return True
    
    # Data types management
    
    def get_data_types(self) -> Dict:
        """Get all data types."""
        return self.model.file_types
    
    def get_data_type_names(self) -> List[str]:
        """Get list of data type names."""
        return list(self.model.file_types.keys())
    
    def get_data_type(self, name: str) -> Optional[Dict]:
        """
        Get a specific data type by name.
        
        Args:
            name: The data type name
            
        Returns:
            Dict with data type info or None if not found
        """
        return self.model.file_types.get(name)
    
    def add_data_type(self, name: str, description: str = '', 
                      directory: str = '', file_extensions: List[str] = None) -> bool:
        """
        Add a new data type.
        
        Args:
            name: The data type name
            description: Description of the data type
            directory: Directory pattern for the data type
            file_extensions: List of file extensions
            
        Returns:
            bool: True if successful, False if name already exists
        """
        if name in self.model.file_types:
            return False
            
        self.model.file_types[name] = {
            'description': description,
            'folder': directory,
            'extensions': file_extensions or []
        }
        
        return True
    
    def remove_data_type(self, name: str) -> bool:
        """
        Remove a data type.
        
        Args:
            name: The data type name to remove
            
        Returns:
            bool: True if successful, False if not found
        """
        if name not in self.model.file_types:
            return False
            
        self.model.file_types.pop(name)
        return True
    
    def update_data_type_description(self, name: str, description: str) -> bool:
        """
        Update the description of a data type.
        
        Args:
            name: The data type name
            description: New description
            
        Returns:
            bool: True if successful, False if not found
        """
        if name not in self.model.file_types:
            return False
            
        self.model.file_types[name]['description'] = description
        return True
    
    def update_data_type_directory(self, name: str, directory: str) -> bool:
        """Legacy method - redirects to update_data_type_folder."""
        return self.update_data_type_folder(name, directory)
    
    def update_data_type_folder(self, name: str, folder: str) -> bool:
        """
        Update the folder of a data type.
        
        Args:
            name: The data type name
            folder: New folder pattern
            
        Returns:
            bool: True if successful, False if not found
        """
        if name not in self.model.file_types:
            return False
            
        self.model.file_types[name]['folder'] = folder
        return True
    
    def update_data_type_extensions(self, name: str, extensions_str: str) -> tuple[bool, str]:
        """
        Update the file extensions of a data type.
        
        Args:
            name: The data type name
            extensions_str: Comma-separated string of extensions
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        if name not in self.model.file_types:
            return False, "Data type not found"
            
        if not FileExtensionValidator.is_valid_extensions(extensions_str):
            return False, 'Please enter valid file extensions separated by ", ".'
            
        extensions = FileExtensionValidator.parse_extensions(extensions_str)
        self.model.file_types[name]['extensions'] = extensions
        return True, ""
    
    def format_extensions_for_display(self, name: str) -> str:
        """
        Get formatted string of file extensions for a data type.
        
        Args:
            name: The data type name
            
        Returns:
            Formatted string of extensions
        """
        data_type = self.get_data_type(name)
        if not data_type:
            return ""
        return FileExtensionValidator.format_extensions(data_type.get('extensions', data_type.get('file_extensions', [])))
    
    # Persistence
    
    def save_configuration(self) -> bool:
        """
        Save the configuration to file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.model.save()
            return True
        except Exception:
            return False
    
    def reload_configuration(self):
        """Reload configuration from file."""
        self.model = OptionFile(self.config_path)