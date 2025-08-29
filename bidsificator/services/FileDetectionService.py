"""Service for detecting file types, modalities, and DICOM folders."""

import os
import pathlib
from typing import Optional, Dict, List


class FileDetectionService:
    """Handles file type detection, modality detection, and DICOM identification."""
    
    # Extension to category mapping
    EXTENSION_TO_CATEGORY = {
        '.nii': 'anat', '.nii.gz': 'anat',
        '.trc': 'ieeg', '.vhdr': 'ieeg', '.edf': 'ieeg',
        '.png': 'photo', '.jpg': 'photo', '.jpeg': 'photo', 
        '.tif': 'photo', '.tiff': 'photo'
    }
    
    # Anatomy patterns for specific modality detection
    ANATOMY_PATTERNS = {
        't1w': 'T1w (anat)', 't1': 'T1w (anat)',
        't2w': 'T2w (anat)', 't2': 'T2w (anat)', 
        'flair': 'FLAIR (anat)',
        't1rho': 'T1rho (anat)',
        't2star': 'T2* (anat)', 't2*': 'T2* (anat)',
        'ct': 'CT (anat)'
    }
    
    # Category to default modality mapping
    CATEGORY_DEFAULTS = {
        'ieeg': 'ieeg (ieeg)',
        'photo': 'photo (ieeg)'
    }
    
    # DICOM file extensions
    DICOM_EXTENSIONS = ['.dcm', '.DCM', '.dicom', '.DICOM']
    
    @classmethod
    def detect_modality_from_file(cls, file_path: str) -> Optional[str]:
        """
        Auto-detect modality from filename and extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected modality string or None if not recognized
        """
        filename = os.path.basename(file_path).lower()
        extension = ''.join(pathlib.Path(file_path).suffixes).lower()
        
        # Get general category from extension
        category = cls.EXTENSION_TO_CATEGORY.get(extension)
        if not category:
            return None
            
        # Match specific patterns for anatomy
        if category == 'anat':
            for pattern, modality in cls.ANATOMY_PATTERNS.items():
                if pattern in filename:
                    return modality
            return 'T1w (anat)'  # Default fallback for anatomy
        
        # Return default for other categories
        return cls.CATEGORY_DEFAULTS.get(category)
    
    @classmethod
    def is_dicom_folder(cls, folder_path: str) -> bool:
        """
        Check if a folder contains DICOM files.
        
        Args:
            folder_path: Path to the folder to check
            
        Returns:
            True if folder contains DICOM files, False otherwise
        """
        if not os.path.isdir(folder_path):
            return False
        
        # Check for common DICOM file extensions
        for root, dirs, files in os.walk(folder_path):
            # Check first 10 files for performance
            for file in files[:10]:
                if any(file.endswith(ext) for ext in cls.DICOM_EXTENSIONS):
                    return True
            
            # Also check files without extensions (common in DICOM)
            no_ext_files = [f for f in files if '.' not in f]
            if len(no_ext_files) > 5:  # Likely DICOM if many files without extensions
                return True
                
        return False
    
    @classmethod
    def get_file_filters(cls) -> Dict[str, str]:
        """
        Get file filters for different modalities.
        
        Returns:
            Dictionary mapping modality keys to file filter strings
        """
        return {
            "(anat)": "Nifti files (*.nii *.nii.gz)",
            "photo (ieeg)": "Image files (*.png *.jpg *.tif)",
            "ieeg (ieeg)": "IEEG files (*.trc *.vhdr *.edf)"
        }
    
    @classmethod
    def get_all_supported_extensions(cls) -> str:
        """
        Get a filter string for all supported file types.
        
        Returns:
            Filter string for QFileDialog with all supported extensions
        """
        return "All supported files (*.nii *.nii.gz *.trc *.vhdr *.edf *.png *.jpg *.jpeg *.tif *.tiff)"
    
    @classmethod
    def get_modality_requirements(cls, modality: str) -> Dict[str, bool]:
        """
        Get UI requirements for a specific modality.
        
        Args:
            modality: The modality string
            
        Returns:
            Dictionary with visibility flags for UI elements
        """
        requirements = {
            'show_session': True,
            'show_task': True,
            'show_contrast': False,
            'show_acquisition': True,
            'show_reconstruction': False
        }
        
        if "(anat)" in modality:
            requirements['show_contrast'] = True
            requirements['show_reconstruction'] = True
            requirements['show_task'] = True  # Tasks shown for all modalities now
        elif "ieeg (ieeg)" in modality:
            requirements['show_task'] = True
        elif "photo (ieeg)" in modality:
            requirements['show_task'] = True
            
        return requirements