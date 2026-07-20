"""
DICOM to NIfTI Converter

Converts DICOM files to BIDS-compliant NIfTI format using dicom2nifti.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any

import dicom2nifti
import pydicom

from .base import FormatConverter

logger = logging.getLogger(__name__)


class DicomToNiftiConverter(FormatConverter):
    """Convert DICOM files to BIDS-compliant NIfTI using dicom2nifti"""

    @property
    def source_extensions(self) -> list[str]:
        # DICOM files can have various extensions or none at all
        return ['.dcm', '.ima', '.dicom', '']

    @property
    def target_format(self) -> str:
        return '.nii.gz'

    @property
    def priority(self) -> int:
        return 1  # Only converter for DICOM files

    @property
    def description(self) -> str:
        return "DICOM → NIfTI (Compressed)"

    def can_convert(self, source_path: Path) -> bool:
        """Check if file/directory contains DICOM data"""
        try:
            if source_path.is_file():
                # Try to read as DICOM file
                pydicom.dcmread(source_path, stop_before_pixels=True)
                return True
            elif source_path.is_dir():
                # Check if directory contains DICOM files
                dicom_files = list(source_path.glob('*.dcm')) + list(source_path.glob('*.ima'))
                if not dicom_files:
                    # Try files without extension
                    for file in source_path.iterdir():
                        if file.is_file():
                            try:
                                pydicom.dcmread(file, stop_before_pixels=True)
                                return True
                            except Exception:
                                continue
                else:
                    # Try to read first DICOM file
                    pydicom.dcmread(dicom_files[0], stop_before_pixels=True)
                    return True
            return False
        except Exception:
            return False

    def convert(self, source_path: Path, output_dir: Path = None) -> Path:
        """Convert DICOM to NIfTI format"""
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())

        # Determine if single file or directory
        if source_path.is_file():
            # For single DICOM file, we need the directory
            dicom_directory = source_path.parent
        else:
            # Directory of DICOM files
            dicom_directory = source_path

        # Convert DICOM to NIfTI
        try:
            dicom2nifti.convert_directory(
                str(dicom_directory),
                str(output_dir),
                compression=True,
                reorient=True
            )

            # Find the generated NIfTI file
            nifti_files = list(output_dir.glob('*.nii.gz'))
            if not nifti_files:
                nifti_files = list(output_dir.glob('*.nii'))

            if not nifti_files:
                raise RuntimeError("No NIfTI file generated from DICOM conversion")

            # Return the first NIfTI file (usually there's only one per series)
            return nifti_files[0]

        except Exception as e:
            raise RuntimeError(f"DICOM to NIfTI conversion failed: {e}") from e

    def extract_metadata(self, source_path: Path) -> dict[str, Any]:
        """Extract metadata from DICOM files"""
        metadata = {}

        try:
            # Get first DICOM file
            if source_path.is_file():
                dcm = pydicom.dcmread(source_path)
            else:
                # Find first DICOM in directory
                dicom_files = list(source_path.glob('*.dcm')) + list(source_path.glob('*.ima'))
                if not dicom_files:
                    # Try files without extension
                    for file in source_path.iterdir():
                        if file.is_file():
                            try:
                                dcm = pydicom.dcmread(file)
                                break
                            except Exception:
                                continue
                    else:
                        return metadata
                else:
                    dcm = pydicom.dcmread(dicom_files[0])

            # Extract standard DICOM metadata
            metadata['Manufacturer'] = str(getattr(dcm, 'Manufacturer', 'Unknown'))
            metadata['ManufacturersModelName'] = str(getattr(dcm, 'ManufacturerModelName', 'Unknown'))
            metadata['InstitutionName'] = str(getattr(dcm, 'InstitutionName', 'Unknown'))
            metadata['InstitutionalDepartmentName'] = str(getattr(dcm, 'InstitutionalDepartmentName', 'Unknown'))

            # MRI-specific metadata
            if hasattr(dcm, 'MagneticFieldStrength'):
                metadata['MagneticFieldStrength'] = float(dcm.MagneticFieldStrength)
            if hasattr(dcm, 'RepetitionTime'):
                metadata['RepetitionTime'] = float(dcm.RepetitionTime) / 1000.0  # Convert ms to seconds
            if hasattr(dcm, 'EchoTime'):
                metadata['EchoTime'] = float(dcm.EchoTime) / 1000.0  # Convert ms to seconds
            if hasattr(dcm, 'FlipAngle'):
                metadata['FlipAngle'] = float(dcm.FlipAngle)
            if hasattr(dcm, 'SliceThickness'):
                metadata['SliceThickness'] = float(dcm.SliceThickness)
            if hasattr(dcm, 'PixelSpacing'):
                metadata['PixelSpacing'] = [float(x) for x in dcm.PixelSpacing]

            # Series and protocol information
            metadata['SeriesDescription'] = str(getattr(dcm, 'SeriesDescription', ''))
            metadata['ProtocolName'] = str(getattr(dcm, 'ProtocolName', ''))
            metadata['SequenceName'] = str(getattr(dcm, 'SequenceName', ''))

            # Patient information (anonymized)
            if hasattr(dcm, 'PatientAge'):
                metadata['PatientAge'] = str(dcm.PatientAge)
            if hasattr(dcm, 'PatientSex'):
                metadata['PatientSex'] = str(dcm.PatientSex)
            if hasattr(dcm, 'PatientWeight'):
                metadata['PatientWeight'] = float(dcm.PatientWeight)

            # Acquisition information
            if hasattr(dcm, 'AcquisitionDate'):
                metadata['AcquisitionDate'] = str(dcm.AcquisitionDate)
            if hasattr(dcm, 'AcquisitionTime'):
                metadata['AcquisitionTime'] = str(dcm.AcquisitionTime)

            # Try to determine modality from series description
            series_desc = metadata.get('SeriesDescription', '').lower()
            protocol = metadata.get('ProtocolName', '').lower()

            if any(x in series_desc + protocol for x in ['t1', 'mprage', 'spgr']):
                metadata['ModalityLabel'] = 'T1w'
                metadata['BidsDatatype'] = 'anat'
            elif any(x in series_desc + protocol for x in ['t2']):
                metadata['ModalityLabel'] = 'T2w'
                metadata['BidsDatatype'] = 'anat'
            elif any(x in series_desc + protocol for x in ['flair']):
                metadata['ModalityLabel'] = 'FLAIR'
                metadata['BidsDatatype'] = 'anat'
            elif any(x in series_desc + protocol for x in ['bold', 'fmri', 'func', 'task']):
                metadata['ModalityLabel'] = 'bold'
                metadata['BidsDatatype'] = 'func'
                metadata['TaskName'] = 'unknown'  # Should be specified by user
            elif any(x in series_desc + protocol for x in ['dwi', 'dti', 'diffusion']):
                metadata['ModalityLabel'] = 'dwi'
                metadata['BidsDatatype'] = 'dwi'
            elif any(x in series_desc + protocol for x in ['fieldmap', 'field_map', 'b0']):
                metadata['BidsDatatype'] = 'fmap'
            else:
                metadata['BidsDatatype'] = 'anat'  # Default to anatomical

        except Exception:
            logger.warning("could not extract full metadata from DICOM", exc_info=True)

        return metadata
