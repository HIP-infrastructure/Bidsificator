"""
BIDS Metadata Extractor Service

Orchestrates extraction of metadata from various file formats to generate
BIDS-compliant TSV files (channels.tsv, events.tsv, etc.).

Uses the converter registry for format detection and delegates to 
format-specific extractors for actual data extraction.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import pandas as pd

from ..converters.registry import ConverterRegistry
from ..core.schema.tsv_schema_mapper import BidsSchemaMapper, ColumnDefinition
from .ContactLabelingParser import ContactLabelingParser

logger = logging.getLogger(__name__)


class BidsMetadataExtractor:
    """
    Central service for extracting BIDS metadata from electrophysiology files
    """
    
    def __init__(self):
        self.converter_registry = ConverterRegistry()
        self.schema_mapper = BidsSchemaMapper()
        self.contact_labeling_parser = ContactLabelingParser()
    
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
    
    def extract_electrodes_tsv(self,
                               file_path: Path,
                               datatype: str = 'ieeg',
                               contact_labeling_file: Optional[Path] = None) -> pd.DataFrame:
        """
        Extract electrodes.tsv data for iEEG files

        Args:
            file_path: Path to the source file
            datatype: BIDS datatype
            contact_labeling_file: Optional path to Excel file with contact labeling data

        Returns:
            BIDS-compliant electrodes DataFrame with optional clinical annotations
        """
        # Get format-specific extractor
        converter = self.converter_registry.get_converter(file_path)

        if converter and hasattr(converter, 'extract_electrodes_data'):
            # Use format-specific extraction
            raw_data = converter.extract_electrodes_data(file_path)
        else:
            # Fallback to generic extraction
            raw_data = self._extract_generic_electrodes(file_path, datatype)

        # If no electrode data but we have a contact labeling file,
        # generate basic electrode entries from channels (without coordinates)
        if len(raw_data) == 0 and contact_labeling_file is not None:
            logger.info("No electrode coordinates found in file. Generating electrodes from channels for contact labeling.")
            raw_data = self._generate_electrodes_from_channels(file_path, datatype)

        # Convert to BIDS-compliant DataFrame
        df = self.schema_mapper.create_compliant_dataframe(
            raw_data, suffix='electrodes', datatype=datatype
        )

        # Merge with contact labeling data if provided
        if contact_labeling_file is not None:
            df = self._merge_contact_labeling_data(df, contact_labeling_file)

        return df
    
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

    def _generate_electrodes_from_channels(self, file_path: Path, datatype: str) -> List[Dict[str, Any]]:
        """
        Generate basic electrode entries from channel names.
        Used when electrode coordinates are not available but we need an electrodes.tsv
        (e.g., to add clinical annotations from contact labeling file).

        Args:
            file_path: Path to the source file
            datatype: BIDS datatype

        Returns:
            List of electrode dictionaries with names (coordinates set to n/a)
        """
        # Extract channels first
        channels_df = self.extract_channels_tsv(file_path, datatype)

        if channels_df.empty or 'name' not in channels_df.columns:
            return []

        # Create basic electrode entries from channel names
        electrodes = []
        for channel_name in channels_df['name']:
            # Only include SEEG/EEG channels (exclude ECG, EOG, etc.)
            if 'type' in channels_df.columns:
                channel_type = channels_df[channels_df['name'] == channel_name]['type'].iloc[0]
                if channel_type not in ['SEEG', 'EEG', 'ECOG', 'DBS']:
                    continue  # Skip non-electrode channels

            electrodes.append({
                'name': channel_name,
                'x': 'n/a',
                'y': 'n/a',
                'z': 'n/a',
                'size': 'n/a',
            })

        return electrodes
    
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

    def _merge_contact_labeling_data(self,
                                     electrodes_df: pd.DataFrame,
                                     contact_labeling_file: Path) -> pd.DataFrame:
        """
        Merge clinical annotations from contact labeling file into electrodes DataFrame

        Args:
            electrodes_df: Base electrodes DataFrame
            contact_labeling_file: Path to Excel file with contact labeling data

        Returns:
            Merged DataFrame with clinical annotations
        """
        try:
            # Parse the contact labeling file
            contact_data = self.contact_labeling_parser.parse_file(contact_labeling_file)

            if not contact_data:
                logger.warning("No contact data found in %s", contact_labeling_file)
                return electrodes_df

            # Validate contact names match
            if 'name' in electrodes_df.columns:
                electrode_names = electrodes_df['name'].tolist()
                validation = self.contact_labeling_parser.validate_against_channels(
                    contact_data, electrode_names
                )

                # Warn about mismatches
                if validation['missing_in_channels']:
                    logger.warning("Contacts in labeling file not found in electrodes: %s",
                                   validation['missing_in_channels'])

                if validation['missing_in_labeling']:
                    logger.warning("Electrodes without labeling data: %s contacts",
                                   len(validation['missing_in_labeling']))

                # Merge annotations into DataFrame (case-insensitive matching)
                for idx, row in electrodes_df.iterrows():
                    contact_name = row.get('name')
                    # Use case-insensitive lookup
                    annotations = self.contact_labeling_parser.get_annotations_for_contact(
                        contact_data, contact_name
                    )
                    if annotations:
                        # Add each annotation as a column value for this row
                        for col, value in annotations.items():
                            electrodes_df.at[idx, col] = value

            return electrodes_df

        except Exception:
            logger.exception("Error merging contact labeling data")
            # Return original DataFrame if merging fails
            return electrodes_df
