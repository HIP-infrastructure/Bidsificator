"""
BIDS Schema Mapper for TSV Files

Maps BIDS schema requirements to TSV file generation, ensuring compliance
with BIDS specification for channels, events, and other tabular data files.
"""

from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import pandas as pd
from dataclasses import dataclass

from .schema_manager import BidsSchemaManager


@dataclass
class ColumnDefinition:
    """Definition of a BIDS TSV column from schema"""
    name: str
    description: str
    data_type: str  # 'string', 'number', 'boolean', 'integer'
    requirement_level: str  # 'required', 'recommended', 'optional'
    format: Optional[str] = None  # 'label', 'index', etc.
    enum: Optional[List[str]] = None  # Allowed values


class BidsSchemaMapper:
    """Maps BIDS schema requirements to TSV file generation"""
    
    def __init__(self):
        self.schema_manager = BidsSchemaManager.get_instance()
        self._column_cache = {}
    
    def get_tsv_column_requirements(self, suffix: str, datatype: str = None) -> Dict[str, ColumnDefinition]:
        """
        Get column requirements for a specific TSV file type
        
        Args:
            suffix: TSV file suffix ('channels', 'events', etc.)
            datatype: BIDS datatype ('ieeg', 'eeg', 'meg', etc.) for context
            
        Returns:
            Dictionary mapping column names to their definitions
        """
        cache_key = f"{suffix}_{datatype or 'generic'}"
        if cache_key in self._column_cache:
            return self._column_cache[cache_key]
        
        columns = {}
        raw_schema = self.schema_manager._raw_schema
        
        # Get column definitions from schema
        schema_columns = raw_schema.get('objects', {}).get('columns', {})
        
        if suffix == 'channels':
            columns.update(self._get_channels_columns(schema_columns, datatype))
        elif suffix == 'events':
            columns.update(self._get_events_columns(schema_columns, datatype))
        elif suffix == 'electrodes':
            columns.update(self._get_electrodes_columns(schema_columns, datatype))
        # Add more TSV types as needed
        
        self._column_cache[cache_key] = columns
        return columns
    
    def _get_channels_columns(self, schema_columns: Dict, datatype: str = None) -> Dict[str, ColumnDefinition]:
        """Get columns for channels.tsv files - dynamically extracted from schema"""
        columns = {}

        # Map schema column keys to BIDS column names
        # Schema uses suffixes like '__channels' to namespace columns
        column_mappings = {
            'name__channels': 'name',
            'type__channels': 'type',
            'units': 'units',
            'sampling_frequency': 'sampling_frequency',
            'status': 'status',
            'group__channel': 'group',
            'low_cutoff': 'low_cutoff',
            'high_cutoff': 'high_cutoff',
            'reference': 'reference',
            'description__channel': 'description',
            'notch': 'notch',
            'status_description': 'status_description'
        }

        # Extract columns from schema
        for schema_key, bids_key in column_mappings.items():
            if schema_key in schema_columns:
                col_def = schema_columns[schema_key]
                columns[bids_key] = ColumnDefinition(
                    name=bids_key,
                    description=col_def.get('description', ''),
                    data_type=col_def.get('type', 'string'),
                    requirement_level=col_def.get('requirement_level', 'optional'),
                    format=col_def.get('format'),
                    enum=col_def.get('enum')
                )

        # Add reference column if not in schema (common for ieeg/eeg)
        if 'reference' not in columns and datatype in ['ieeg', 'eeg', 'meg']:
            columns['reference'] = ColumnDefinition(
                name='reference',
                description='Specification of the reference electrode(s)',
                data_type='string',
                requirement_level='recommended'
            )

        # BIDS requires name/type/units in channels.tsv. The schema column
        # objects don't carry a requirement_level, so these otherwise default to
        # 'optional' and the validator can never flag a missing required column.
        # Upgrade them to 'required' (mirrors the required-column fallbacks in
        # _get_events_columns / _get_electrodes_columns) while preserving any
        # schema-derived metadata.
        required_channel_columns = {
            'name': 'Label of the channel',
            'type': 'Type of channel',
            'units': 'Physical unit of the value represented in this channel',
        }
        for col_name, description in required_channel_columns.items():
            existing = columns.get(col_name)
            columns[col_name] = ColumnDefinition(
                name=col_name,
                description=existing.description if existing else description,
                data_type=existing.data_type if existing else 'string',
                requirement_level='required',
                format=existing.format if existing else None,
                enum=existing.enum if existing else None,
            )

        return columns
    
    def _get_events_columns(self, schema_columns: Dict, datatype: str = None) -> Dict[str, ColumnDefinition]:
        """Get columns for events.tsv files - dynamically extracted from schema"""
        columns = {}

        # Core events.tsv columns defined in BIDS schema
        core_event_columns = ['onset', 'duration', 'trial_type', 'response_time', 'stim_file', 'HED']

        # Extract from schema
        for col_name in core_event_columns:
            if col_name in schema_columns:
                col_def = schema_columns[col_name]
                columns[col_name] = ColumnDefinition(
                    name=col_name,
                    description=col_def.get('description', ''),
                    data_type=col_def.get('type', 'string'),
                    requirement_level=col_def.get('requirement_level', 'optional'),
                    format=col_def.get('format'),
                    enum=col_def.get('enum')
                )

        # Ensure required columns are present (fallback if not in schema)
        if 'onset' not in columns:
            columns['onset'] = ColumnDefinition(
                name='onset',
                description='Onset time of event in seconds',
                data_type='number',
                requirement_level='required'
            )

        if 'duration' not in columns:
            columns['duration'] = ColumnDefinition(
                name='duration',
                description='Duration of event in seconds',
                data_type='number',
                requirement_level='required'
            )

        # Add 'value' column (arbitrary but commonly used for trigger codes)
        if 'value' not in columns:
            columns['value'] = ColumnDefinition(
                name='value',
                description='Event value (e.g., trigger code, stimulus identifier)',
                data_type='string',
                requirement_level='optional'
            )

        return columns
    
    def _get_electrodes_columns(self, schema_columns: Dict, datatype: str = None) -> Dict[str, ColumnDefinition]:
        """Get columns for electrodes.tsv files (for iEEG)"""
        columns = {}

        # Core electrode columns
        electrode_columns = {
            'name': 'Electrode name',
            'x': 'X coordinate',
            'y': 'Y coordinate',
            'z': 'Z coordinate',
            'size': 'Surface area or volume',
            'hemisphere': 'Hemisphere (L/R)',
            'group': 'Electrode group'
        }

        for col_name, description in electrode_columns.items():
            data_type = 'number' if col_name in ['x', 'y', 'z', 'size'] else 'string'
            columns[col_name] = ColumnDefinition(
                name=col_name,
                description=description,
                data_type=data_type,
                requirement_level='required' if col_name == 'name' else 'optional'
            )

        # Clinical annotation columns (for SEEG contact labeling)
        # These are all optional and populated from external labeling files
        clinical_columns = {
            'within_ez': ('Whether contact is within the epileptogenic zone', 'string'),
            'within_lesion': ('Whether contact is within the lesion (EI value)', 'string'),
            'spikes_wake': ('Presence of spikes during wakefulness', 'string'),
            'spikes_wake_rate': ('Rate of spikes during wakefulness', 'number'),
            'spikes_sleep': ('Presence of spikes during sleep', 'string'),
            'spikes_sleep_rate': ('Rate of spikes during sleep', 'number'),
            'ripples_wake': ('Presence of ripples during wakefulness', 'string'),
            'ripples_wake_rate': ('Rate of ripples during wakefulness', 'number'),
            'ripples_sleep': ('Presence of ripples during sleep', 'string'),
            'ripples_sleep_rate': ('Rate of ripples during sleep', 'number'),
            'fast_ripples_wake': ('Presence of fast ripples during wakefulness', 'string'),
            'fast_ripples_wake_rate': ('Rate of fast ripples during wakefulness', 'number'),
            'fast_ripples_sleep': ('Presence of fast ripples during sleep', 'string'),
            'fast_ripples_sleep_rate': ('Rate of fast ripples during sleep', 'number'),
            'rftc': ('Radiofrequency thermocoagulation status', 'string'),
            'resected': ('Whether contact was resected', 'string'),
        }

        for col_name, (description, data_type) in clinical_columns.items():
            columns[col_name] = ColumnDefinition(
                name=col_name,
                description=description,
                data_type=data_type,
                requirement_level='optional'
            )

        return columns
    
    def validate_tsv_dataframe(self, df: pd.DataFrame, suffix: str, datatype: str = None) -> List[str]:
        """
        Validate a TSV DataFrame against BIDS schema requirements
        
        Args:
            df: DataFrame to validate
            suffix: TSV file suffix ('channels', 'events', etc.)
            datatype: BIDS datatype for context
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        requirements = self.get_tsv_column_requirements(suffix, datatype)
        
        # Check required columns are present
        required_cols = {name for name, col_def in requirements.items() 
                        if col_def.requirement_level == 'required'}
        missing_cols = required_cols - set(df.columns)
        
        for col in missing_cols:
            errors.append(f"Required column '{col}' missing from {suffix}.tsv")
        
        # Check data types for existing columns
        for col_name in df.columns:
            if col_name in requirements:
                col_def = requirements[col_name]
                expected_type = col_def.data_type
                
                # Basic type checking
                if expected_type == 'number':
                    if not pd.api.types.is_numeric_dtype(df[col_name]):
                        non_numeric = df[col_name].dropna()
                        if len(non_numeric) > 0 and not all(str(x).replace('.', '').replace('-', '').isdigit() or str(x) == 'n/a' for x in non_numeric):
                            errors.append(f"Column '{col_name}' should contain numeric values")
                
                # Check enum constraints if present  
                if col_def.enum:
                    invalid_values = set(df[col_name].dropna()) - set(col_def.enum + ['n/a'])
                    if invalid_values:
                        errors.append(f"Column '{col_name}' contains invalid values: {invalid_values}")
        
        return errors
    
    def create_compliant_dataframe(self, data: List[Dict[str, Any]], suffix: str, datatype: str = None) -> pd.DataFrame:
        """
        Create a BIDS-compliant DataFrame from raw data
        
        Args:
            data: List of dictionaries with raw data
            suffix: TSV file suffix ('channels', 'events', etc.)
            datatype: BIDS datatype for context
            
        Returns:
            BIDS-compliant DataFrame
        """
        if not data:
            # Return empty DataFrame with proper columns
            requirements = self.get_tsv_column_requirements(suffix, datatype)
            return pd.DataFrame({col_name: [] for col_name in requirements.keys()})
        
        df = pd.DataFrame(data)
        requirements = self.get_tsv_column_requirements(suffix, datatype)
        
        # Ensure all required columns are present
        for col_name, col_def in requirements.items():
            if col_name not in df.columns:
                if col_def.requirement_level == 'required':
                    # Add with n/a default for required missing columns
                    df[col_name] = 'n/a'
                elif col_def.requirement_level == 'recommended':
                    # Add recommended columns with appropriate defaults
                    default_value = self._get_default_value(col_def.data_type)
                    df[col_name] = default_value
        
        # Apply data type conversions
        for col_name in df.columns:
            if col_name in requirements:
                col_def = requirements[col_name]
                df[col_name] = self._convert_column_type(df[col_name], col_def)
        
        # Reorder columns to match BIDS specification order
        if suffix == 'channels':
            # BIDS channels.tsv has a specific column order
            bids_order = ['name', 'type', 'units', 'low_cutoff', 'high_cutoff', 'sampling_frequency', 
                         'status', 'group', 'reference', 'description', 'notch', 'status_description']
            ordered_columns = [col for col in bids_order if col in df.columns]
            extra_columns = [col for col in df.columns if col not in bids_order]
        else:
            # For other TSV types, use schema order
            ordered_columns = [col for col in requirements.keys() if col in df.columns]
            extra_columns = [col for col in df.columns if col not in requirements]
        
        df = df[ordered_columns + extra_columns]
        
        return df
    
    def _get_default_value(self, data_type: str) -> Any:
        """Get appropriate default value for a data type"""
        defaults = {
            'string': 'n/a',
            'number': 0,
            'integer': 0,
            'boolean': False
        }
        return defaults.get(data_type, 'n/a')
    
    def _convert_column_type(self, series: pd.Series, col_def: ColumnDefinition) -> pd.Series:
        """Convert series to appropriate data type"""
        if col_def.data_type == 'number':
            # Convert to numeric, keeping 'n/a' as string
            try:
                return pd.to_numeric(series)
            except (ValueError, TypeError):
                return series  # Keep original if conversion fails
        elif col_def.data_type == 'integer':
            # Convert to integer where possible
            numeric = pd.to_numeric(series, errors='coerce')
            return numeric.fillna(series)  # Keep original for non-numeric
        elif col_def.data_type == 'boolean':
            # Convert to boolean
            return series.map(lambda x: x if pd.isna(x) or x == 'n/a' else bool(x))
        
        # Default to string
        return series.astype(str)