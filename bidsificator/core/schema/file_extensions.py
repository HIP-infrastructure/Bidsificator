"""
BIDS File Extension Registry

Manages BIDS-compliant file extensions and format mappings.
Since the BIDS schema doesn't contain explicit file extension mappings,
this registry maintains the authoritative list of supported formats.
"""

from pathlib import Path
from typing import Any

# BIDS-compliant file extensions
# Update this when BIDS specification changes
BIDS_FILE_EXTENSIONS = {
    'ieeg': {
        'data_files': {
            '.edf': {'format': 'European Data Format', 'official': True},
            '.vhdr': {'format': 'BrainVision', 'official': True},
            '.eeg': {'format': 'BrainVision', 'official': True, 'requires': ['.vhdr', '.vmrk']},
            '.vmrk': {'format': 'BrainVision', 'official': True, 'auxiliary': True},
            '.bdf': {'format': 'Biosemi', 'official': False},
            '.set': {'format': 'EEGLAB', 'official': False},
            '.fdt': {'format': 'EEGLAB', 'official': False, 'auxiliary': True}
        },
        'metadata_files': {
            '.json': 'metadata',
            '_channels.tsv': 'channels',
            '_events.tsv': 'events',
            '_electrodes.tsv': 'electrodes',
            '_coordsystem.json': 'coordinate system',
            '_photo.jpg': 'photo'
        }
    },
    'eeg': {
        'data_files': {
            '.edf': {'format': 'European Data Format', 'official': True},
            '.vhdr': {'format': 'BrainVision', 'official': True},
            '.eeg': {'format': 'BrainVision', 'official': True, 'requires': ['.vhdr', '.vmrk']},
            '.vmrk': {'format': 'BrainVision', 'official': True, 'auxiliary': True},
            '.bdf': {'format': 'Biosemi', 'official': False},
            '.set': {'format': 'EEGLAB', 'official': False},
            '.fdt': {'format': 'EEGLAB', 'official': False, 'auxiliary': True}
        },
        'metadata_files': {
            '.json': 'metadata',
            '_channels.tsv': 'channels',
            '_events.tsv': 'events',
            '_electrodes.tsv': 'electrodes',
            '_coordsystem.json': 'coordinate system'
        }
    },
    'anat': {
        'data_files': {
            '.nii': {'format': 'NIfTI', 'official': True},
            '.nii.gz': {'format': 'Compressed NIfTI', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata'
        }
    },
    'func': {
        'data_files': {
            '.nii': {'format': 'NIfTI', 'official': True},
            '.nii.gz': {'format': 'Compressed NIfTI', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata',
            '_events.tsv': 'events'
        }
    },
    'dwi': {
        'data_files': {
            '.nii': {'format': 'NIfTI', 'official': True},
            '.nii.gz': {'format': 'Compressed NIfTI', 'official': True},
            '.bval': {'format': 'b-values', 'official': True, 'auxiliary': True},
            '.bvec': {'format': 'b-vectors', 'official': True, 'auxiliary': True}
        },
        'metadata_files': {
            '.json': 'metadata'
        }
    },
    'fmap': {
        'data_files': {
            '.nii': {'format': 'NIfTI', 'official': True},
            '.nii.gz': {'format': 'Compressed NIfTI', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata'
        }
    },
    'perf': {
        'data_files': {
            '.nii': {'format': 'NIfTI', 'official': True},
            '.nii.gz': {'format': 'Compressed NIfTI', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata',
            '_aslcontext.tsv': 'ASL context'
        }
    },
    'pet': {
        'data_files': {
            '.nii': {'format': 'NIfTI', 'official': True},
            '.nii.gz': {'format': 'Compressed NIfTI', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata'
        }
    },
    'meg': {
        'data_files': {
            '.fif': {'format': 'Neuromag', 'official': True},
            '.con': {'format': 'KIT/Yokogawa', 'official': True},
            '.raw': {'format': 'KIT/Yokogawa', 'official': True},
            '.ave': {'format': 'KIT/Yokogawa', 'official': True},
            '.mrk': {'format': 'KIT/Yokogawa', 'official': True},
            '.sqd': {'format': 'KIT/Yokogawa', 'official': True},
            '.dat': {'format': 'CTF', 'official': True},
            '.meg4': {'format': 'CTF', 'official': True},
            '.res4': {'format': 'CTF', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata',
            '_channels.tsv': 'channels',
            '_events.tsv': 'events'
        }
    },
    'nirs': {
        'data_files': {
            '.snirf': {'format': 'SNIRF', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata',
            '_channels.tsv': 'channels',
            '_events.tsv': 'events',
            '_coordsystem.json': 'coordinate system',
            '_optodes.tsv': 'optodes'
        }
    },
    'motion': {
        'data_files': {
            '.tsv': {'format': 'Tab-separated values', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata',
            '_channels.tsv': 'channels',
            '_events.tsv': 'events'
        }
    },
    'beh': {
        'data_files': {
            '.tsv': {'format': 'Tab-separated values', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata',
            '_events.tsv': 'events'
        }
    },
    'micr': {
        'data_files': {
            '.tif': {'format': 'TIFF', 'official': True},
            '.tiff': {'format': 'TIFF', 'official': True},
            '.ome.tif': {'format': 'OME-TIFF', 'official': True},
            '.ome.tiff': {'format': 'OME-TIFF', 'official': True},
            '.ome.zarr': {'format': 'OME-Zarr', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata'
        }
    },
    'mrs': {
        'data_files': {
            '.nii': {'format': 'NIfTI-MRS', 'official': True},
            '.nii.gz': {'format': 'Compressed NIfTI-MRS', 'official': True}
        },
        'metadata_files': {
            '.json': 'metadata'
        }
    }
}


class FileExtensionRegistry:
    """Registry for BIDS file extensions"""

    def __init__(self, schema_manager):
        self.schema = schema_manager
        self.extensions = BIDS_FILE_EXTENSIONS

    def get_supported_extensions(self, datatype: str) -> list[str]:
        """Get supported file extensions for a datatype"""
        if datatype not in self.extensions:
            return []

        extensions = []
        for ext, info in self.extensions[datatype].get('data_files', {}).items():
            if not info.get('auxiliary', False):
                extensions.append(ext)

        return extensions

    def detect_datatype(self, file_path: Path) -> str | None:
        """Detect datatype from file extension"""
        ext = file_path.suffix.lower()
        filename = file_path.name.lower()

        # Handle compound extensions
        if filename.endswith('.nii.gz'):
            ext = '.nii.gz'
        elif filename.endswith('.ome.tif'):
            ext = '.ome.tif'
        elif filename.endswith('.ome.tiff'):
            ext = '.ome.tiff'
        elif filename.endswith('.ome.zarr'):
            ext = '.ome.zarr'

        for datatype, type_info in self.extensions.items():
            if ext in type_info.get('data_files', {}):
                if ext in ['.nii', '.nii.gz']:
                    return self._detect_nifti_type(filename)
                elif ext == '.tsv':
                    return self._detect_tsv_type(filename)
                else:
                    return datatype

        return None

    def _detect_nifti_type(self, filename: str) -> str:
        """Detect if NIfTI is anatomical, functional, or other type"""
        # Check for anatomical patterns
        anat_patterns = ['t1w', 't2w', 'flair', 'pd', 't1', 't2', 'ct', 't1rho', 't2star']
        for pattern in anat_patterns:
            if pattern in filename:
                return 'anat'

        # Check for functional patterns
        func_patterns = ['bold', 'task-']
        for pattern in func_patterns:
            if pattern in filename:
                return 'func'

        # Check for DWI patterns
        dwi_patterns = ['dwi', 'dti']
        for pattern in dwi_patterns:
            if pattern in filename:
                return 'dwi'

        # Check for fieldmap patterns
        fmap_patterns = ['fieldmap', 'phasediff', 'phase1', 'phase2', 'magnitude']
        for pattern in fmap_patterns:
            if pattern in filename:
                return 'fmap'

        # Check for perfusion patterns
        perf_patterns = ['asl', 'cbf', 'cbv']
        for pattern in perf_patterns:
            if pattern in filename:
                return 'perf'

        # Check for PET patterns
        pet_patterns = ['pet']
        for pattern in pet_patterns:
            if pattern in filename:
                return 'pet'

        # Check for MRS patterns
        mrs_patterns = ['svs', 'csi']
        for pattern in mrs_patterns:
            if pattern in filename:
                return 'mrs'

        # Default to anatomical
        return 'anat'

    def _detect_tsv_type(self, filename: str) -> str:
        """Detect TSV file type from filename"""
        if '_motion' in filename or 'motion_' in filename:
            return 'motion'
        elif '_beh' in filename or 'beh_' in filename:
            return 'beh'
        else:
            # Could be motion or beh, default to beh
            return 'beh'

    def validate_file_format(self, file_path: Path, datatype: str) -> bool:
        """Validate if file format is BIDS-compliant"""
        ext = file_path.suffix.lower()
        filename = file_path.name.lower()

        # Handle compound extensions
        if filename.endswith('.nii.gz'):
            ext = '.nii.gz'
        elif filename.endswith('.ome.tif'):
            ext = '.ome.tif'
        elif filename.endswith('.ome.tiff'):
            ext = '.ome.tiff'
        elif filename.endswith('.ome.zarr'):
            ext = '.ome.zarr'

        if datatype not in self.extensions:
            return False

        file_info = self.extensions[datatype]['data_files'].get(ext)
        if not file_info:
            return False

        # Check for required auxiliary files
        required = file_info.get('requires', [])
        for req_ext in required:
            aux_file = file_path.with_suffix(req_ext)
            if not aux_file.exists():
                return False

        return True

    def get_required_auxiliary_files(self, file_path: Path, datatype: str) -> list[str]:
        """Get required auxiliary files for a given file"""
        ext = file_path.suffix.lower()
        filename = file_path.name.lower()

        # Handle compound extensions
        if filename.endswith('.nii.gz'):
            ext = '.nii.gz'

        if datatype in self.extensions:
            file_info = self.extensions[datatype]['data_files'].get(ext, {})
            return file_info.get('requires', [])

        return []

    def get_metadata_files(self, datatype: str) -> dict[str, str]:
        """Get metadata file types for a datatype"""
        if datatype not in self.extensions:
            return {}

        return self.extensions[datatype].get('metadata_files', {})

    def get_format_info(self, datatype: str, extension: str) -> dict[str, Any]:
        """Get format information for a specific extension"""
        if datatype not in self.extensions:
            return {}

        return self.extensions[datatype].get('data_files', {}).get(extension, {})
