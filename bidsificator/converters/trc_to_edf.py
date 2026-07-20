"""
Micromed TRC to EDF Converter

Converts Micromed TRC files to BIDS-compliant EDF format using MNE-Python.
"""

from pathlib import Path
from typing import Dict, Any, List
import logging
import tempfile
import warnings

import mne
import mne.io
import mne.export
import neo
import numpy as np

from .base import FormatConverter

logger = logging.getLogger(__name__)


class TrcToEdfConverter(FormatConverter):
    """Convert Micromed TRC files to BIDS-compliant EDF using MNE"""
    
    @property
    def source_extensions(self) -> List[str]:
        return ['.trc']
    
    @property
    def target_format(self) -> str:
        return '.edf'
    
    @property
    def priority(self) -> int:
        return 1  # Higher priority = preferred converter for TRC files
    
    @property
    def description(self) -> str:
        return "Micromed TRC → EDF (European Data Format)"
    
    def can_convert(self, source_path: Path) -> bool:
        """Check if file is a valid TRC file"""
        if not source_path.exists() or source_path.suffix.lower() != '.trc':
            return False
            
        # Try to read the file header to validate it's a real TRC file
        try:
            # Use neo to read Micromed TRC files
            reader = neo.io.MicromedIO(filename=str(source_path))
            # Try to read headers to validate
            block = reader.read_block(lazy=True)
            return len(block.segments) > 0 and len(block.segments[0].analogsignals) > 0
        except Exception:
            return False
    
    def convert(self, source_path: Path, output_dir: Path = None) -> Path:
        """Convert TRC to EDF format using MNE"""
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())
        
        output_path = output_dir / source_path.with_suffix('.edf').name
        
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
            # Convert from µV to V (EDF typically expects volts)
            if hasattr(sig, 'units') and str(sig.units) == 'uV':
                sig_data = sig_data * 1e-6  # µV to V
            elif hasattr(sig, 'units') and str(sig.units) == 'mV':
                sig_data = sig_data * 1e-3  # mV to V
            # If already in V or unknown units, keep as is
            data_list.append(sig_data)
        
        data = np.concatenate(data_list, axis=0)
        
        # Get sampling frequency (assume all signals have same sampling rate)
        sfreq = float(analog_signals[0].sampling_rate.magnitude)
        
        # Create channel names and types (EDF requires ≤16 character names)
        ch_names = []
        ch_types = []
        for i, sig in enumerate(analog_signals):
            n_channels = sig.shape[1] if len(sig.shape) > 1 else 1
            if hasattr(sig, 'name') and sig.name:
                if n_channels == 1:
                    # Truncate channel name to 16 characters for EDF compatibility
                    clean_name = self._clean_channel_name(sig.name)
                    ch_names.append(clean_name)
                    ch_types.append('eeg')  # Default to EEG
                else:
                    for j in range(n_channels):
                        # Truncate and add channel index
                        base_name = self._clean_channel_name(sig.name, max_len=13)  # Leave space for _j
                        ch_names.append(f"{base_name}_{j}")
                        ch_types.append('eeg')
            else:
                if n_channels == 1:
                    ch_names.append(f'CH_{len(ch_names)}')
                    ch_types.append('eeg')
                else:
                    for j in range(n_channels):
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
        
        # Calculate appropriate physical range based on actual data
        data_min = np.min(data)
        data_max = np.max(data)
        data_range = max(abs(data_min), abs(data_max))
        
        # Add 20% margin to handle any data spikes during conversion
        physical_range = data_range * 1.2
        
        # Ensure minimum range for EDF format (at least ±1mV)
        physical_range = max(physical_range, 1e-3)
        
        logger.debug("TRC data range: %.2e to %.2e V", data_min, data_max)
        logger.debug("Setting EDF physical range: ±%.2e V", physical_range)
        
        # Export to EDF format with calculated physical range
        raw.export(str(output_path), fmt='edf', physical_range=(-physical_range, physical_range), overwrite=True)
        
        # Close the raw object to free memory
        raw.close()
        
        return output_path
    
    def _clean_channel_name(self, name: str, max_len: int = 16) -> str:
        """Clean and truncate channel name for EDF compatibility"""
        if not name:
            return "UNKNOWN"
            
        # Remove problematic characters that might cause issues
        clean_name = name.replace("'", "").replace(" ", "").replace("-", "").replace("+", "")
        
        # Truncate to maximum length
        if len(clean_name) > max_len:
            clean_name = clean_name[:max_len]
        
        # Ensure it's not empty after cleaning
        if not clean_name:
            clean_name = "CH"
            
        return clean_name
    
    def extract_metadata(self, source_path: Path) -> Dict[str, Any]:
        """Extract metadata from TRC file using MNE"""
        metadata = {
            'Manufacturer': 'Micromed',
            'ManufacturersModelName': 'SystemPlus Evolution',
            'PowerLineFrequency': 50,  # Default for Europe, could be 60 for US
        }
        
        try:
            # Use neo to read TRC file
            reader = neo.io.MicromedIO(filename=str(source_path))
            block = reader.read_block(lazy=True)
            
            if block.segments and block.segments[0].analogsignals:
                segment = block.segments[0]
                analog_signals = segment.analogsignals
                
                # Extract basic metadata from neo
                first_signal = analog_signals[0]
                metadata.update({
                    'SamplingFrequency': float(first_signal.sampling_rate.magnitude),
                    'RecordingType': 'continuous',
                    'RecordingDuration': float(first_signal.duration.magnitude),
                    'ChannelCount': sum(sig.shape[1] if len(sig.shape) > 1 else 1 for sig in analog_signals),
                })
                
                # Extract channel information
                total_channels = metadata['ChannelCount']
                metadata.update({
                    'EEGChannelCount': total_channels,  # Assume all are EEG by default
                    'iEEGReference': 'unknown',  # TRC files don't typically specify reference
                })
                
                # Try to extract recording date from block annotations
                if hasattr(block, 'rec_datetime') and block.rec_datetime:
                    metadata['RecordingDate'] = block.rec_datetime.strftime('%Y-%m-%d')
                    metadata['RecordingTime'] = block.rec_datetime.strftime('%H:%M:%S')
                
                # Extract file-specific annotations if available
                if block.annotations:
                    # Look for any useful metadata in annotations
                    for ann in block.annotations:
                        if hasattr(ann, 'name') and hasattr(ann, 'description'):
                            # Could extract additional metadata from annotations
                            pass
                
        except Exception:
            logger.warning("could not extract full metadata from TRC file", exc_info=True)
            # Add minimum required metadata if extraction fails
            metadata.update({
                'SamplingFrequency': 1024,  # Common default
                'iEEGReference': 'unknown',
                'RecordingType': 'continuous'
            })
            
        return metadata