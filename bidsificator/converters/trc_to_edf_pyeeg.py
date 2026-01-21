"""
TRC to EDF converter using PyEEGFormat library
Reliable, production-tested conversion for Micromed TRC files
"""

import platform
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..converters.base import FormatConverter


class TrcToEdfConverterPyEEG(FormatConverter):
    """Convert Micromed TRC files to EDF using PyEEGFormat"""
    
    def __init__(self):
        super().__init__()
        self.wrapper = self._import_platform_wrapper()
        self._priority = 10  # Higher priority than MNE-based converter
    
    @property
    def source_extensions(self) -> List[str]:
        """File extensions this converter handles"""
        return ['.trc']
    
    @property
    def target_format(self) -> str:
        """BIDS-compliant format this converter produces"""
        return '.edf'
    
    @property
    def priority(self) -> int:
        """Higher priority for PyEEGFormat converter"""
        return self._priority
    
    @property
    def description(self) -> str:
        """Human-readable description"""
        return "Micromed TRC → EDF using PyEEGFormat (recommended)"
    
    def _import_platform_wrapper(self):
        """Import the platform-specific PyEEGFormat wrapper"""
        os_name = platform.system()
        machine = platform.machine()
        
        try:
            if os_name == "Darwin":
                if "arm" in machine.lower():
                    from ..core.PyEEGFormat import wrappermacarm as wrapper
                else:
                    raise ImportError(f"No PyEEGFormat wrapper available for Darwin {machine}")
            elif os_name == "Windows":
                from ..core.PyEEGFormat import wrapperwinamd64 as wrapper
            elif os_name == "Linux":
                if "x86_64" in machine.lower():
                    from ..core.PyEEGFormat import wrapperlinux as wrapper
                else:
                    raise ImportError(f"No PyEEGFormat wrapper available for Linux {machine}")
            else:
                raise ImportError(f"Unsupported operating system: {os_name}")
                
            return wrapper
            
        except ImportError as e:
            print(f"PyEEGFormat import error: {e}")
            raise
    
    def can_convert(self, source_path: Path) -> bool:
        """Check if this converter can handle the file"""
        if not source_path.exists():
            return False
        
        # Check extension
        if source_path.suffix.lower() != '.trc':
            return False
        
        # Try to open the file with PyEEGFormat to verify it's valid
        try:
            # PyEEGFormat requires byte strings and a boolean flag
            file_obj = self.wrapper.PyIFile(str(source_path).encode('utf-8'), False)
            # If we can get basic info, file is valid
            _ = file_obj.get_sampling_frequency()
            return True
        except Exception:
            return False
    
    def convert(self, source_path: Path, output_dir: Path = None) -> Path:
        """
        Convert TRC file to EDF format
        
        Args:
            source_path: Path to source TRC file
            output_dir: Directory for output file
            
        Returns:
            Path to converted EDF file
        """
        if output_dir is None:
            output_dir = source_path.parent
            
        output_path = output_dir / f"{source_path.stem}.edf"
        
        # PyEEGFormat conversion - simple and reliable
        try:
            self.wrapper.convert_file(
                str(source_path).encode('utf-8'),
                str(output_path).encode('utf-8'),
                False
            )
        except Exception as e:
            raise RuntimeError(f"Failed to convert {source_path}: {e}")
        
        if not output_path.exists():
            raise RuntimeError(f"Conversion failed - output file not created: {output_path}")
        
        return output_path
    
    def extract_metadata(self, source_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from TRC file for BIDS JSON sidecar
        
        Args:
            source_path: Path to TRC file
            
        Returns:
            Dictionary of BIDS metadata fields
        """
        metadata = {}
        
        try:
            # Open TRC file with PyEEGFormat
            file_obj = self.wrapper.PyIFile(str(source_path).encode('utf-8'), False)
            
            # Basic required metadata
            sfreq = file_obj.get_sampling_frequency()
            metadata['SamplingFrequency'] = float(sfreq)
            
            # Recording information
            n_samples = file_obj.get_number_samples()
            metadata['RecordingDuration'] = n_samples / sfreq
            metadata['RecordingType'] = 'continuous'
            
            # Hardware information
            metadata['Manufacturer'] = 'Micromed'
            metadata['ManufacturersModelName'] = 'SystemPlus Evolution'
            
            # Power line frequency (Europe default, could be enhanced with region detection)
            metadata['PowerLineFrequency'] = 50
            
            # Channel information for reference
            metadata['EEGChannelCount'] = file_obj.get_electrode_count()
            
            # Hardware filters if available
            filters = self._extract_hardware_filters(file_obj)
            if filters:
                metadata['HardwareFilters'] = filters
            
            # Reference information
            ref_info = self._extract_reference_info(file_obj)
            if ref_info:
                metadata['EEGReference'] = ref_info
                
        except Exception as e:
            # Return minimal metadata on error
            print(f"Warning: Could not extract full metadata from {source_path}: {e}")
            metadata = {
                'Manufacturer': 'Micromed',
                'PowerLineFrequency': 50,
                'RecordingType': 'continuous'
            }
        
        return metadata
    
    def _extract_hardware_filters(self, file_obj) -> Optional[Dict[str, Any]]:
        """Extract hardware filter information from TRC file"""
        try:
            # Get filter info from first electrode as representative
            if file_obj.get_electrode_count() > 0:
                electrode = file_obj.get_electrode(0)
                
                filters = {}
                
                # High-pass filter
                hp_freq = electrode.PrefilteringHighPassLimit()
                if hp_freq and hp_freq > 0:
                    filters['HighpassFilter'] = {
                        'Frequency': float(hp_freq),
                        'Type': 'Hardware'
                    }
                
                # Low-pass filter
                lp_freq = electrode.PrefilteringLowPassLimit()
                if lp_freq and lp_freq > 0:
                    filters['LowpassFilter'] = {
                        'Frequency': float(lp_freq),
                        'Type': 'Hardware'
                    }
                
                return filters if filters else None
                
        except Exception:
            return None
    
    def _extract_reference_info(self, file_obj) -> Optional[str]:
        """Extract reference electrode information"""
        try:
            # Check first few electrodes for reference info
            references = set()
            for i in range(min(5, file_obj.get_electrode_count())):
                electrode = file_obj.get_electrode(i)
                ref_label = electrode.ReferenceLabel()
                if ref_label:
                    # Decode if bytes
                    if isinstance(ref_label, bytes):
                        ref_label = ref_label.decode('utf-8', errors='ignore')
                    if ref_label and ref_label != 'n/a':
                        references.add(ref_label)
            
            if references:
                # If all electrodes have same reference, return it
                if len(references) == 1:
                    return list(references)[0]
                else:
                    return "mixed"
                    
        except Exception:
            pass
        
        return None
    
    def extract_channels_data(self, source_path: Path) -> List[Dict[str, Any]]:
        """
        Extract channel information from TRC file for channels.tsv generation
        
        Args:
            source_path: Path to TRC file
            
        Returns:
            List of dictionaries with channel data for BIDS channels.tsv
        """
        channels_data = []
        
        try:
            # Open TRC file with PyEEGFormat
            file_obj = self.wrapper.PyIFile(str(source_path).encode('utf-8'), False)
            
            sampling_frequency = file_obj.get_sampling_frequency()
            electrode_count = file_obj.get_electrode_count()
            
            for i in range(electrode_count):
                electrode = file_obj.get_electrode(i)
                
                # Extract electrode information
                site_name = electrode.Label()
                if isinstance(site_name, bytes):
                    site_name = site_name.decode('utf-8', errors='ignore')
                
                site_unit = electrode.Unit()
                if isinstance(site_unit, bytes):
                    site_unit = site_unit.decode('utf-8', errors='ignore')
                
                # Get filter information
                lowpass_limit = electrode.PrefilteringLowPassLimit()
                highpass_limit = electrode.PrefilteringHighPassLimit()
                
                # Get reference information
                ref_label = electrode.ReferenceLabel()
                if isinstance(ref_label, bytes):
                    ref_label = ref_label.decode('utf-8', errors='ignore')
                
                # Determine electrode type and group based on naming pattern
                electrode_type = 'SEEG'  # Default for iEEG
                electrode_group = 'n/a'
                
                # Parse electrode name to determine group (e.g., A'1 -> group A)
                if re.match(r"^[A-Z]+\'*[0-9]{1,2}$", site_name):
                    electrode_group = re.sub(r'\d+', '', site_name).replace("'", "")
                
                channel_data = {
                    'name': site_name,
                    'type': electrode_type,
                    'units': site_unit if site_unit else 'µV',
                    'low_cutoff': float(highpass_limit) if highpass_limit and highpass_limit > 0 else 'n/a',
                    'high_cutoff': float(lowpass_limit) if lowpass_limit and lowpass_limit > 0 else 'n/a',
                    'reference': ref_label if ref_label and ref_label != 'n/a' else 'n/a',
                    'group': electrode_group,
                    'sampling_frequency': float(sampling_frequency),
                    'description': 'n/a',
                    'notch': 50,  # European default
                    'status': 'good',
                    'status_description': 'n/a'
                }
                
                channels_data.append(channel_data)
            
        except Exception as e:
            print(f"Warning: Could not extract channel data from {source_path}: {e}")
            # Return empty list - will trigger fallback in metadata extractor
            return []
        
        return channels_data
    
    def extract_events_data(self, source_path: Path) -> List[Dict[str, Any]]:
        """
        Extract events/triggers from TRC file for events.tsv generation
        
        Args:
            source_path: Path to TRC file
            
        Returns:
            List of dictionaries with event data for BIDS events.tsv
        """
        events_data = []
        
        try:
            # Open TRC file with PyEEGFormat
            file_obj = self.wrapper.PyIFile(str(source_path).encode('utf-8'), False)
            
            sampling_frequency = file_obj.get_sampling_frequency()
            trigger_count = file_obj.get_trigger_count()
            note_count = file_obj.get_note_count()
            
            # Collect all events (triggers and notes) with their timestamps
            all_events = []
            
            # Add triggers
            for i in range(trigger_count):
                trigger = file_obj.get_trigger(i)
                onset = trigger.Sample() / sampling_frequency
                
                event_data = {
                    'onset': float(onset),
                    'duration': 0.0,  # Triggers are typically instantaneous  
                    'trial_type': 'trigger',  # Generic trigger type, specific code goes in value column
                    'response_time': 'n/a',
                    'stim_file': 'n/a',
                    'value': str(trigger.Code())  # Trigger code value - BIDS arbitrary column for EEG/iEEG
                }
                all_events.append(event_data)
            
            # Add notes/annotations
            for i in range(note_count):
                note = file_obj.get_note(i)
                onset = note.Sample() / sampling_frequency
                
                note_text = note.Description()
                if isinstance(note_text, bytes):
                    note_text = note_text.decode('utf-8', errors='ignore')
                
                event_data = {
                    'onset': float(onset),
                    'duration': 'n/a',  # Notes typically don't have duration
                    'trial_type': note_text if note_text else 'annotation',  # Use actual annotation text as trial_type
                    'response_time': 'n/a',
                    'stim_file': 'n/a'
                }
                all_events.append(event_data)
            
            # Sort events chronologically by onset time
            all_events.sort(key=lambda x: x['onset'])
            events_data = all_events
            
        except Exception as e:
            print(f"Warning: Could not extract event data from {source_path}: {e}")
            # Return empty list - will result in empty events.tsv
            return []
        
        return events_data
    
    def extract_electrodes_data(self, source_path: Path) -> List[Dict[str, Any]]:
        """
        Extract electrode position information from TRC file (if available)
        
        Args:
            source_path: Path to TRC file
            
        Returns:
            List of dictionaries with electrode position data
        """
        # TRC files typically don't contain electrode positions
        # This would need to be provided separately or extracted from other sources
        # For now, return empty list - electrodes.tsv is optional for iEEG
        return []