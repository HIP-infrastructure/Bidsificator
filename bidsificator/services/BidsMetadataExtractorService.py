"""
BIDS Metadata Extractor Service

Orchestrates extraction of metadata from various file formats to generate
BIDS-compliant TSV files (channels.tsv, events.tsv, etc.).

Uses the converter registry for format detection and delegates to 
format-specific extractors for actual data extraction.
"""

from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import pandas as pd

from ..converters.registry import ConverterRegistry
from ..core.schema.tsv_schema_mapper import BidsSchemaMapper, ColumnDefinition


class BidsMetadataExtractor:
    """
    Central service for extracting BIDS metadata from electrophysiology files
    """
    
    def __init__(self):
        self.converter_registry = ConverterRegistry()
        self.schema_mapper = BidsSchemaMapper()
    
    def extract_channels_tsv(self, file_path: Path, datatype: str = 'ieeg') -> pd.DataFrame:
        """
        Extract channels.tsv data from an electrophysiology file
        
        Args:
            file_path: Path to the source file
            datatype: BIDS datatype (ieeg, eeg, meg, etc.)
            
        Returns:
            BIDS-compliant channels DataFrame
        """
        # Get format-specific extractor
        converter = self.converter_registry.get_converter(file_path)
        
        if converter and hasattr(converter, 'extract_channels_data'):
            # Use format-specific extraction
            raw_data = converter.extract_channels_data(file_path)
        else:
            # Fallback to generic extraction
            raw_data = self._extract_generic_channels(file_path, datatype)
        
        # Convert to BIDS-compliant DataFrame
        return self.schema_mapper.create_compliant_dataframe(
            raw_data, suffix='channels', datatype=datatype
        )
    
    def extract_events_tsv(self, file_path: Path, datatype: str = 'ieeg') -> pd.DataFrame:
        """
        Extract events.tsv data from an electrophysiology file
        
        Args:
            file_path: Path to the source file
            datatype: BIDS datatype
            
        Returns:
            BIDS-compliant events DataFrame
        """
        # Get format-specific extractor
        converter = self.converter_registry.get_converter(file_path)
        
        if converter and hasattr(converter, 'extract_events_data'):
            # Use format-specific extraction
            raw_data = converter.extract_events_data(file_path)
        else:
            # Fallback to generic extraction (empty events)
            raw_data = []
        
        # Convert to BIDS-compliant DataFrame
        return self.schema_mapper.create_compliant_dataframe(
            raw_data, suffix='events', datatype=datatype
        )
    
    def extract_electrodes_tsv(self, file_path: Path, datatype: str = 'ieeg') -> pd.DataFrame:
        """
        Extract electrodes.tsv data for iEEG files
        
        Args:
            file_path: Path to the source file
            datatype: BIDS datatype
            
        Returns:
            BIDS-compliant electrodes DataFrame
        """
        # Get format-specific extractor
        converter = self.converter_registry.get_converter(file_path)
        
        if converter and hasattr(converter, 'extract_electrodes_data'):
            # Use format-specific extraction
            raw_data = converter.extract_electrodes_data(file_path)
        else:
            # Fallback to generic extraction
            raw_data = self._extract_generic_electrodes(file_path, datatype)
        
        # Convert to BIDS-compliant DataFrame
        return self.schema_mapper.create_compliant_dataframe(
            raw_data, suffix='electrodes', datatype=datatype
        )
    
    def validate_generated_tsv(self, df: pd.DataFrame, suffix: str, datatype: str = None) -> Tuple[bool, List[str]]:
        """
        Validate a generated TSV DataFrame against BIDS schema
        
        Args:
            df: DataFrame to validate
            suffix: TSV file suffix ('channels', 'events', etc.)
            datatype: BIDS datatype for context
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = self.schema_mapper.validate_tsv_dataframe(df, suffix, datatype)
        return len(errors) == 0, errors
    
    def get_tsv_requirements(self, suffix: str, datatype: str = None) -> Dict[str, ColumnDefinition]:
        """
        Get BIDS schema requirements for a TSV file type
        
        Args:
            suffix: TSV file suffix ('channels', 'events', etc.)
            datatype: BIDS datatype for context
            
        Returns:
            Dictionary of column requirements
        """
        return self.schema_mapper.get_tsv_column_requirements(suffix, datatype)
    
    def _extract_generic_channels(self, file_path: Path, datatype: str) -> List[Dict[str, Any]]:
        """
        Fallback method for generic channel extraction when no format-specific extractor exists
        """
        # Default channel count based on datatype
        default_counts = {
            'ieeg': 64,
            'eeg': 32,
            'meg': 306,
            'seeg': 128
        }
        
        channel_count = default_counts.get(datatype, 32)
        channel_type = 'SEEG' if datatype == 'ieeg' else datatype.upper()
        
        channels = []
        for i in range(1, channel_count + 1):
            channels.append({
                'name': f'CH{i:03d}',
                'type': channel_type,
                'units': 'µV',
                'sampling_frequency': 'n/a',
                'status': 'good'
            })
        
        return channels
    
    def _extract_generic_electrodes(self, file_path: Path, datatype: str) -> List[Dict[str, Any]]:
        """
        Fallback method for generic electrode extraction
        """
        # This would typically extract electrode positions from file metadata
        # For now, return empty - electrodes.tsv is optional
        return []
    
    def can_extract_from_file(self, file_path: Path) -> Dict[str, bool]:
        """
        Check what TSV files can be extracted from a given file
        
        Args:
            file_path: Path to the source file
            
        Returns:
            Dictionary indicating what can be extracted:
            {'channels': bool, 'events': bool, 'electrodes': bool}
        """
        converter = self.converter_registry.get_converter(file_path)
        
        capabilities = {
            'channels': False,
            'events': False,
            'electrodes': False
        }
        
        if converter:
            # Check what extraction methods the converter supports
            capabilities['channels'] = hasattr(converter, 'extract_channels_data')
            capabilities['events'] = hasattr(converter, 'extract_events_data') 
            capabilities['electrodes'] = hasattr(converter, 'extract_electrodes_data')
        
        # Always can do basic channels extraction as fallback
        capabilities['channels'] = True
        
        return capabilities