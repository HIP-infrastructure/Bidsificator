"""
BIDS constants and defaults
"""

from typing import Dict, List

# Default metadata values
DEFAULT_METADATA_VALUES = {
    'UNKNOWN': 'unknown',
    'NOT_AVAILABLE': 'n/a',
    'GOOD_STATUS': 'good',
    'BAD_STATUS': 'bad'
}

# Default suffix mappings by datatype
DEFAULT_SUFFIXES: Dict[str, str] = {
    'ieeg': 'ieeg',
    'eeg': 'eeg',
    'meg': 'meg',
    'anat': 'T1w',
    'func': 'bold', 
    'dwi': 'dwi',
    'fmap': 'phasediff',
    'perf': 'asl',
    'pet': 'pet',
    'micr': 'TEM',
    'beh': 'beh',
    'motion': 'motion',
    'nirs': 'nirs',
    'mrs': 'svs'
}

# Entity ordering for BIDS filenames
# Based on common BIDS practice, but should ideally come from schema
ENTITY_ORDER: List[str] = [
    'sub',
    'ses', 
    'task',
    'acq',
    'ce',
    'rec',
    'dir',
    'run',
    'echo',
    'flip',
    'inv',
    'mt',
    'part',
    'recording',
    'proc',
    'space',
    'split',
    'chunk',
    'sample',
    'tracksys',
    'stain',
    'mod',
    'hemi',
    'res',
    'den',
    'label',
    'desc'
]

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