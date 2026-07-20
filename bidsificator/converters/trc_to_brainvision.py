"""
Micromed TRC to BrainVision Converter

Converts Micromed TRC files to BIDS-compliant BrainVision format using MNE-Python.
"""

import tempfile
from pathlib import Path
from typing import Any

import mne
import mne.export
import mne.io
import neo
import numpy as np

from .base import FormatConverter
from .trc_to_edf import TrcToEdfConverter


class TrcToBrainVisionConverter(FormatConverter):
    """Convert Micromed TRC files to BIDS-compliant BrainVision format using MNE"""

    @property
    def source_extensions(self) -> list[str]:
        return ['.trc']

    @property
    def target_format(self) -> str:
        return '.vhdr'  # BrainVision header file

    @property
    def priority(self) -> int:
        return 0  # Lower priority than EDF

    @property
    def description(self) -> str:
        return "Micromed TRC → BrainVision (.vhdr/.vmrk/.eeg)"

    def can_convert(self, source_path: Path) -> bool:
        """Check if file is a valid TRC file"""
        # Use the same validation as EDF converter
        edf_converter = TrcToEdfConverter()
        return edf_converter.can_convert(source_path)

    def convert(self, source_path: Path, output_dir: Path = None) -> Path:
        """Convert TRC to BrainVision format using MNE"""
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())

        base_name = source_path.stem
        vhdr_path = output_dir / f"{base_name}.vhdr"

        # Read TRC file with neo and convert to MNE Raw
        reader = neo.io.MicromedIO(filename=str(source_path))
        block = reader.read_block()

        # Get the first segment and its analog signals
        segment = block.segments[0]
        analog_signals = segment.analogsignals

        if not analog_signals:
            raise RuntimeError("No analog signals found in TRC file")

        # Combine all analog signals and convert to float32 for better compatibility
        data_list = []
        for sig in analog_signals:
            sig_data = sig.magnitude.T.astype(np.float32)
            # Keep data in original units (µV) for BrainVision format
            # BrainVision can handle µV units well
            data_list.append(sig_data)

        data = np.concatenate(data_list, axis=0)

        # Get sampling frequency (assume all signals have same sampling rate)
        sfreq = float(analog_signals[0].sampling_rate.magnitude)

        # Create channel names and types
        ch_names = []
        ch_types = []
        for _i, sig in enumerate(analog_signals):
            n_channels = sig.shape[1] if len(sig.shape) > 1 else 1
            if hasattr(sig, 'name') and sig.name:
                if n_channels == 1:
                    ch_names.append(sig.name)
                    ch_types.append('eeg')
                else:
                    for j in range(n_channels):
                        ch_names.append(f"{sig.name}_{j}")
                        ch_types.append('eeg')
            else:
                if n_channels == 1:
                    ch_names.append(f'CH_{len(ch_names)}')
                    ch_types.append('eeg')
                else:
                    for _ in range(n_channels):
                        ch_names.append(f'CH_{len(ch_names)}')
                        ch_types.append('eeg')

        # Ensure we have the right number of channel names
        if len(ch_names) != data.shape[0]:
            ch_names = [f'CH_{i}' for i in range(data.shape[0])]
            ch_types = ['eeg'] * data.shape[0]

        # Create MNE info object
        info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)

        # Create MNE Raw object
        raw = mne.io.RawArray(data, info)

        # Export to BrainVision format
        # MNE will create .vhdr, .vmrk, and .eeg files
        raw.export(str(vhdr_path), fmt='brainvision', overwrite=True)

        # Close the raw object
        raw.close()

        return vhdr_path  # Return the header file path

    def extract_metadata(self, source_path: Path) -> dict[str, Any]:
        """Extract metadata from TRC file"""
        # Use the same metadata extraction as EDF converter
        edf_converter = TrcToEdfConverter()
        return edf_converter.extract_metadata(source_path)
