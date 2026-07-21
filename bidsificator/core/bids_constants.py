"""
BIDS constants and defaults

NOTE: This module is being migrated to schema-driven design.
Hardcoded values are being progressively replaced with dynamic schema extraction.
"""


# Default metadata values
DEFAULT_METADATA_VALUES = {
    'UNKNOWN': 'unknown',
    'NOT_AVAILABLE': 'n/a',
    'GOOD_STATUS': 'good',
    'BAD_STATUS': 'bad'
}

def get_default_suffix_for_datatype(datatype: str) -> str:
    """
    Get the default suffix for a given datatype from BIDS schema.

    Prioritizes main data file suffixes over metadata file suffixes.
    For example, for 'ieeg' datatype, returns 'ieeg' not 'channels'.

    Args:
        datatype: BIDS datatype (e.g., 'ieeg', 'anat', 'func')

    Returns:
        Default suffix for the datatype. Returns the datatype name itself if
        no specific default is found in the schema.
    """
    from bidsificator.core.schema import BidsSchemaManager

    manager = BidsSchemaManager.get_instance()

    # Get datatype definition from schema
    if datatype in manager.datatypes:
        dt = manager.get_datatype(datatype)

        if not dt.suffixes:
            return datatype

        # Metadata file suffixes that should not be used as defaults
        metadata_suffixes = {
            'channels', 'electrodes', 'coordsystem', 'events', 'physio', 'stim',
            'headshape', 'markers', 'scans', 'sessions', 'participants',
            'aslcontext', 'asllabeling', 'blood'
        }

        # First, try to find suffix matching datatype name (e.g., 'ieeg' in ieeg datatype)
        if datatype in dt.suffixes:
            return datatype

        # For anatomical data, prioritize common MRI sequences
        if datatype == 'anat':
            preferred_anat = ['T1w', 'T2w', 'FLAIR', 'T2star', 'PDw']
            for pref in preferred_anat:
                if pref in dt.suffixes:
                    return pref

        # Filter out metadata suffixes and select first remaining suffix
        data_suffixes = [s for s in dt.suffixes if s not in metadata_suffixes]

        if data_suffixes:
            return data_suffixes[0]

        # Fallback to first suffix if all are metadata
        return dt.suffixes[0]

    # Fallback: return datatype name as suffix
    return datatype

# Legacy compatibility: Keep DEFAULT_SUFFIXES as a dict-like accessor
# This allows existing code using DEFAULT_SUFFIXES.get(datatype) to continue working
class _DefaultSuffixesAccessor:
    """Dict-like accessor for backward compatibility"""

    def get(self, datatype: str, default: str = None) -> str:
        """Get default suffix with fallback"""
        result = get_default_suffix_for_datatype(datatype)
        return result if result else (default if default else datatype)

    def __getitem__(self, datatype: str) -> str:
        """Dict-like access"""
        return get_default_suffix_for_datatype(datatype)

DEFAULT_SUFFIXES = _DefaultSuffixesAccessor()

_entity_order_cache: list[str] | None = None

def get_entity_order() -> list[str]:
    """
    Get canonical entity ordering from BIDS schema.

    Returns entity keys in the order they should appear in BIDS filenames.
    This is schema-driven and will automatically update with schema changes.

    Returns:
        List of entity keys in canonical order (e.g., ['sub', 'ses', 'task', ...])
    """
    global _entity_order_cache

    # Cache the result to avoid repeated schema queries
    if _entity_order_cache is None:
        from bidsificator.core.schema import BidsSchemaManager
        manager = BidsSchemaManager.get_instance()
        _entity_order_cache = manager.get_entity_order()

    return _entity_order_cache

# Backward compatibility: ENTITY_ORDER is now fully schema-driven
# This is populated on first import and cached
ENTITY_ORDER = get_entity_order()

# Default channel configurations
DEFAULT_CHANNEL_COUNTS = {
    'ieeg': 64,
    'eeg': 64,
    'meg': 306,  # Typical for Neuromag systems
    'nirs': 32
}

# File extensions by category
EPHYS_EXTENSIONS = ['.edf', '.vhdr', '.eeg', '.vmrk', '.bdf', '.set', '.fdt']
IMAGING_EXTENSIONS = ['.nii', '.nii.gz']
MEG_EXTENSIONS = ['.fif', '.con', '.raw', '.ave', '.mrk', '.sqd', '.dat', '.meg4', '.res4']
NIRS_EXTENSIONS = ['.snirf']

# All BIDS data file extensions (excluding metadata)
BIDS_DATA_EXTENSIONS = (
    EPHYS_EXTENSIONS +
    IMAGING_EXTENSIONS +
    MEG_EXTENSIONS +
    NIRS_EXTENSIONS
)

# Metadata file extensions
METADATA_EXTENSIONS = ['.json', '.tsv', '.bval', '.bvec']

# Curated display labels for the modality dropdowns, keyed by BIDS datatype.
# Each entry is a list of (display label, BIDS suffix) pairs. This is a
# deliberately hand-picked presentation subset (e.g. "T2* (anat)" shown for
# suffix "T2star"), not the full per-datatype suffix list the schema exposes,
# so it lives here as a single definition rather than being derived from the
# schema. Both modality dropdowns — the Import Files tab (MainWindow) and the
# File Editor — read this so they stay in lock-step from one source of truth.
MODALITY_DISPLAY_MAPPING: dict[str, list[tuple[str, str]]] = {
    'anat': [
        ('T1w (anat)', 'T1w'),
        ('T2w (anat)', 'T2w'),
        ('T1rho (anat)', 'T1rho'),
        ('T2* (anat)', 'T2star'),
        ('FLAIR (anat)', 'FLAIR'),
        ('CT (anat)', 'CT')
    ],
    'ieeg': [
        ('ieeg (ieeg)', 'ieeg'),
        ('photo (ieeg)', 'photo')
    ],
    'eeg': [
        ('eeg (eeg)', 'eeg')
    ],
    'func': [
        ('BOLD (func)', 'bold')
    ],
    'dwi': [
        ('DWI (dwi)', 'dwi')
    ],
    'fmap': [
        ('fieldmap (fmap)', 'fieldmap')
    ],
    'perf': [
        ('ASL (perf)', 'asl')
    ],
    'beh': [
        ('events (beh)', 'events')
    ]
}
