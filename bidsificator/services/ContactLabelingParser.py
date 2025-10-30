"""
SEEG Contact Labeling Parser

Parses Excel files containing clinical annotations for SEEG contacts
and converts them to BIDS-compliant electrodes.tsv additional columns.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd


class ContactLabelingParser:
    """Parser for SEEG contact labeling Excel files"""

    # Expected column structure in the Excel file
    # Columns that have both indicator (y/n/na) and rate/value
    PAIRED_COLUMNS = {
        'spikes (wakefulness)': ('spikes_wake', 'spikes_wake_rate'),
        'spikes (sleep)': ('spikes_sleep', 'spikes_sleep_rate'),
        'ripples (wakefulness)': ('ripples_wake', 'ripples_wake_rate'),
        'ripples (sleep)': ('ripples_sleep', 'ripples_sleep_rate'),
        'fast ripples (wakefulness)': ('fast_ripples_wake', 'fast_ripples_wake_rate'),
        'fast ripples (sleep)': ('fast_ripples_sleep', 'fast_ripples_sleep_rate'),
    }

    # Single value columns
    SINGLE_COLUMNS = {
        'within the EZ': 'within_ez',
        'within the lesion': 'within_lesion',
        'RFTC': 'rftc',
        'Resected': 'resected'
    }

    def __init__(self):
        """Initialize the parser"""
        # Store a mapping from lowercase contact names to original case
        self._contact_case_mapping = {}

    def parse_file(self, file_path: Path) -> Dict[str, Dict[str, Any]]:
        """
        Parse SEEG contact labeling Excel file

        Args:
            file_path: Path to Excel file

        Returns:
            Dictionary mapping contact names to their clinical annotations
            Example: {'Y1': {'within_ez': 'y', 'spikes_wake': 'y', 'spikes_wake_rate': 5.2, ...}}

        Raises:
            ValueError: If file structure is invalid
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Contact labeling file not found: {file_path}")

        if file_path.suffix.lower() not in ['.xlsx', '.xls']:
            raise ValueError(f"File must be Excel format (.xlsx or .xls): {file_path}")

        # Read Excel file
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}")

        # Validate structure
        self._validate_structure(df)

        # Parse data
        contact_data = self._parse_dataframe(df)

        return contact_data

    def _validate_structure(self, df: pd.DataFrame):
        """
        Validate that the Excel file has expected column structure

        Args:
            df: DataFrame from Excel file

        Raises:
            ValueError: If structure is invalid
        """
        if df.empty:
            raise ValueError("Excel file is empty")

        # Check for contact column
        if 'contact' not in df.columns:
            raise ValueError("Excel file must have a 'contact' column")

        # Check for at least some expected columns
        expected_columns = list(self.SINGLE_COLUMNS.keys()) + list(self.PAIRED_COLUMNS.keys())
        found_columns = [col for col in expected_columns if col in df.columns]

        if len(found_columns) < 2:
            raise ValueError(
                f"Excel file must contain at least 2 expected columns. "
                f"Expected columns: {expected_columns}"
            )

    def _parse_dataframe(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Parse DataFrame into contact annotation dictionary

        Args:
            df: DataFrame from Excel file

        Returns:
            Dictionary mapping contact names to annotations
        """
        contact_data = {}

        for idx, row in df.iterrows():
            contact_name = row.get('contact')

            # Skip if no contact name or if it's the header row
            if pd.isna(contact_name) or contact_name in ['NaN', 'nan', None]:
                continue

            # Skip format hint rows (e.g., "y/n/na")
            if isinstance(contact_name, str) and any(x in contact_name.lower() for x in ['y/n', 'rate', 'value']):
                continue

            contact_name = str(contact_name).strip()
            if not contact_name:
                continue

            # Store both original case and lowercase for case-insensitive matching
            contact_name_lower = contact_name.lower()
            self._contact_case_mapping[contact_name_lower] = contact_name

            # Initialize annotations for this contact
            annotations = {}

            # Parse single-value columns
            for excel_col, bids_col in self.SINGLE_COLUMNS.items():
                if excel_col in df.columns:
                    value = row.get(excel_col)
                    if not pd.isna(value):
                        annotations[bids_col] = self._normalize_value(value)

            # Parse paired columns (indicator + rate)
            for excel_base_col, (bids_indicator, bids_rate) in self.PAIRED_COLUMNS.items():
                # Look for the indicator column and the next column (which should be rate)
                if excel_base_col in df.columns:
                    # Get indicator value
                    indicator_value = row.get(excel_base_col)
                    if not pd.isna(indicator_value):
                        annotations[bids_indicator] = self._normalize_value(indicator_value)

                    # Find the rate column (usually right after the indicator column)
                    col_idx = df.columns.get_loc(excel_base_col)
                    if col_idx + 1 < len(df.columns):
                        rate_col = df.columns[col_idx + 1]
                        rate_value = row.get(rate_col)
                        if not pd.isna(rate_value):
                            # Try to convert to number
                            try:
                                annotations[bids_rate] = float(rate_value)
                            except (ValueError, TypeError):
                                annotations[bids_rate] = self._normalize_value(rate_value)

            # Only add contact if it has at least some annotations
            if annotations:
                contact_data[contact_name] = annotations

        return contact_data

    def _normalize_value(self, value: Any) -> Any:
        """
        Normalize values to BIDS-compliant format

        Args:
            value: Raw value from Excel

        Returns:
            Normalized value (lowercase y/n/na for indicators, original for numbers)
        """
        if pd.isna(value):
            return 'n/a'

        # Convert to string and check if it's an indicator
        str_value = str(value).strip().lower()

        # Normalize common indicator values
        if str_value in ['y', 'yes', 'n', 'no', 'na', 'n/a', 'nd', 'n/d']:
            # Standardize to y/n/na/nd
            if str_value in ['y', 'yes']:
                return 'y'
            elif str_value in ['n', 'no']:
                return 'n'
            elif str_value in ['nd', 'n/d']:
                return 'nd'
            else:
                return 'n/a'

        # Return original value if not an indicator (e.g., numeric values)
        return value

    def validate_against_channels(self,
                                  contact_data: Dict[str, Dict[str, Any]],
                                  channel_names: List[str]) -> Dict[str, List[str]]:
        """
        Validate that contact names match channel names (case-insensitive)

        Args:
            contact_data: Parsed contact annotation data
            channel_names: List of channel names from channels.tsv

        Returns:
            Dictionary with validation results:
            {
                'matched': [...],  # Contacts found in both (using channel name case)
                'missing_in_channels': [...],  # Contacts in Excel but not in channels
                'missing_in_labeling': [...]  # Channels without labeling data
            }
        """
        # Create case-insensitive sets
        contact_set_lower = {name.lower(): name for name in contact_data.keys()}
        channel_set_lower = {name.lower(): name for name in channel_names}

        # Find matches (case-insensitive)
        matched_lower = set(contact_set_lower.keys()) & set(channel_set_lower.keys())
        matched = [channel_set_lower[name_lower] for name_lower in matched_lower]

        # Find contacts not in channels
        missing_in_channels_lower = set(contact_set_lower.keys()) - set(channel_set_lower.keys())
        missing_in_channels = [contact_set_lower[name_lower] for name_lower in missing_in_channels_lower]

        # Find channels without labeling
        missing_in_labeling_lower = set(channel_set_lower.keys()) - set(contact_set_lower.keys())
        missing_in_labeling = [channel_set_lower[name_lower] for name_lower in missing_in_labeling_lower]

        return {
            'matched': matched,
            'missing_in_channels': missing_in_channels,
            'missing_in_labeling': missing_in_labeling
        }

    def get_annotations_for_contact(self,
                                   contact_data: Dict[str, Dict[str, Any]],
                                   contact_name: str) -> Dict[str, Any]:
        """
        Get annotations for a specific contact (case-insensitive)

        Args:
            contact_data: Parsed contact annotation data
            contact_name: Name of the contact

        Returns:
            Dictionary of annotations for the contact (empty if not found)
        """
        # Try exact match first
        if contact_name in contact_data:
            return contact_data[contact_name]

        # Try case-insensitive match
        contact_name_lower = contact_name.lower()
        for key in contact_data.keys():
            if key.lower() == contact_name_lower:
                return contact_data[key]

        return {}
