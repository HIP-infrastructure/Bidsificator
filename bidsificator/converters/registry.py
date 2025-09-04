"""
Converter Registry

Manages all available format converters with automatic discovery and priority-based selection.
"""

from typing import Dict, List, Optional
from pathlib import Path
from .base import FormatConverter


class ConverterRegistry:
    """Registry for all format converters"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.converters: Dict[str, List[FormatConverter]] = {}
            self._register_default_converters()
            ConverterRegistry._initialized = True
    
    def _register_default_converters(self):
        """Register built-in converters - automatically discovers and registers all converters"""
        
        # TRC converters (multiple options for same source format)
        # PyEEGFormat converter - higher priority, more reliable
        try:
            from .trc_to_edf_pyeeg import TrcToEdfConverterPyEEG
            self.register(TrcToEdfConverterPyEEG())  # Primary choice (priority 10)
        except ImportError as e:
            print(f"Warning: Could not import PyEEGFormat TRC to EDF converter: {e}")
            
        # MNE-based converter as fallback
        try:
            from .trc_to_edf import TrcToEdfConverter
            self.register(TrcToEdfConverter())  # Fallback choice (priority 1)
        except ImportError as e:
            print(f"Warning: Could not import MNE TRC to EDF converter: {e}")
        
        try:
            from .trc_to_brainvision import TrcToBrainVisionConverter
            self.register(TrcToBrainVisionConverter())  # Alternative (priority 0)
        except ImportError as e:
            print(f"Warning: Could not import TRC to BrainVision converter: {e}")
        
        # DICOM converter
        try:
            from .dicom_to_nifti import DicomToNiftiConverter
            self.register(DicomToNiftiConverter())
        except ImportError as e:
            print(f"Warning: Could not import DICOM converter: {e}")
    
    def register(self, converter: FormatConverter):
        """Register a format converter"""
        for ext in converter.source_extensions:
            ext = ext.lower()  # Normalize extension
            if ext not in self.converters:
                self.converters[ext] = []
            self.converters[ext].append(converter)
            
        print(f"Registered converter: {converter.description}")
    
    def get_converter(self, file_path: Path, target_format: str = None) -> Optional[FormatConverter]:
        """Get appropriate converter for file"""
        ext = file_path.suffix.lower()
        
        if ext in self.converters:
            available_converters = [c for c in self.converters[ext] if c.can_convert(file_path)]
            
            if not available_converters:
                return None
            
            # If target format specified, find matching converter
            if target_format:
                for converter in available_converters:
                    if converter.target_format == target_format:
                        return converter
                # If no exact match, return None (don't force incompatible conversion)
                return None
            
            # Otherwise, return highest priority converter
            return max(available_converters, key=lambda c: c.priority)
        
        return None
    
    def get_all_converters(self, file_path: Path) -> List[FormatConverter]:
        """Get all available converters for a file, sorted by priority"""
        ext = file_path.suffix.lower()
        
        if ext in self.converters:
            available_converters = [c for c in self.converters[ext] if c.can_convert(file_path)]
            # Sort by priority (highest first)
            return sorted(available_converters, key=lambda c: c.priority, reverse=True)
        
        return []
    
    def get_available_target_formats(self, file_path: Path) -> List[str]:
        """Get all possible target formats for a source file"""
        converters = self.get_all_converters(file_path)
        return [converter.target_format for converter in converters]
    
    def needs_conversion(self, file_path: Path) -> bool:
        """Check if file needs conversion"""
        return self.get_converter(file_path) is not None
    
    def get_supported_source_formats(self) -> Dict[str, List[str]]:
        """Get all supported source formats for UI display"""
        formats = {}
        for ext_list in self.converters.values():
            for converter in ext_list:
                for ext in converter.source_extensions:
                    if ext not in formats:
                        formats[ext] = []
                    formats[ext].append(f"{converter.__class__.__name__} → {converter.target_format}")
        return formats
    
    def get_converter_by_name(self, converter_name: str) -> Optional[FormatConverter]:
        """Get converter by class name for explicit selection"""
        for converter_list in self.converters.values():
            for converter in converter_list:
                if converter.__class__.__name__ == converter_name:
                    return converter
        return None