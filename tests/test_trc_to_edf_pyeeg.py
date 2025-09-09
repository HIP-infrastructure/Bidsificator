#!/usr/bin/env python
"""
Comprehensive tests for PyEEGFormat-based TRC to EDF converter
"""

import tempfile
import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from bidsificator.converters.trc_to_edf_pyeeg import TrcToEdfConverterPyEEG


class TestTrcToEdfConverterPyEEG:
    """Test suite for PyEEGFormat-based TRC to EDF converter"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Mock the PyEEGFormat wrapper
        self.mock_wrapper = MagicMock()
        
        # Mock PyIFile object
        self.mock_file = MagicMock()
        self.mock_file.get_sampling_frequency.return_value = 512.0
        self.mock_file.get_number_samples.return_value = 512000
        self.mock_file.get_electrode_count.return_value = 64
        self.mock_file.get_trigger_count.return_value = 10
        self.mock_file.get_note_count.return_value = 5
        
        # Mock electrode object
        self.mock_electrode = MagicMock()
        self.mock_electrode.Label.return_value = b"A'1"
        self.mock_electrode.Unit.return_value = b"uV"
        self.mock_electrode.PrefilteringHighPassLimit.return_value = 0.5
        self.mock_electrode.PrefilteringLowPassLimit.return_value = 70.0
        self.mock_electrode.ReferenceLabel.return_value = b"REF"
        
        self.mock_file.get_electrode.return_value = self.mock_electrode
        
        # Configure wrapper mock
        self.mock_wrapper.PyIFile.return_value = self.mock_file
        self.mock_wrapper.convert_file = MagicMock()
    
    @patch('bidsificator.converters.trc_to_edf_pyeeg.platform.system')
    @patch('bidsificator.converters.trc_to_edf_pyeeg.platform.machine')
    def test_platform_import_mac_arm(self, mock_machine, mock_system):
        """Test correct wrapper import for Mac ARM platform"""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"
        
        with patch('bidsificator.converters.trc_to_edf_pyeeg.TrcToEdfConverterPyEEG._import_platform_wrapper') as mock_import:
            mock_import.return_value = self.mock_wrapper
            converter = TrcToEdfConverterPyEEG()
            assert converter.wrapper is not None
    
    def test_converter_properties(self):
        """Test converter properties and metadata"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            assert converter.source_extensions == ['.trc']
            assert converter.target_format == '.edf'
            assert converter.priority == 10  # Higher priority than MNE converter
            assert "PyEEGFormat" in converter.description
    
    def test_can_convert_valid_file(self):
        """Test can_convert with valid TRC file"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            # Create temporary TRC file
            with tempfile.NamedTemporaryFile(suffix='.trc', delete=False) as tmp:
                tmp_path = Path(tmp.name)
                
            try:
                # Test can_convert
                assert converter.can_convert(tmp_path) == True
                
                # Verify PyIFile was called with correct arguments
                self.mock_wrapper.PyIFile.assert_called_with(str(tmp_path).encode('utf-8'), False)
                self.mock_file.get_sampling_frequency.assert_called_once()
            finally:
                tmp_path.unlink()
    
    def test_can_convert_invalid_extension(self):
        """Test can_convert rejects non-TRC files"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            # Create temporary non-TRC file
            with tempfile.NamedTemporaryFile(suffix='.edf', delete=False) as tmp:
                tmp_path = Path(tmp.name)
                
            try:
                assert converter.can_convert(tmp_path) == False
            finally:
                tmp_path.unlink()
    
    def test_can_convert_nonexistent_file(self):
        """Test can_convert with nonexistent file"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            fake_path = Path("/nonexistent/file.trc")
            assert converter.can_convert(fake_path) == False
    
    def test_convert_success(self):
        """Test successful TRC to EDF conversion"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create source and output paths
                source_path = Path(tmpdir) / "test.trc"
                source_path.touch()
                output_dir = Path(tmpdir) / "output"
                output_dir.mkdir()
                
                expected_output = output_dir / "test.edf"
                
                # Mock successful conversion
                def mock_convert(src, dst):
                    Path(dst.decode('utf-8')).touch()
                
                self.mock_wrapper.convert_file.side_effect = mock_convert
                
                # Perform conversion
                result = converter.convert(source_path, output_dir)
                
                # Verify conversion was called with correct arguments
                self.mock_wrapper.convert_file.assert_called_once_with(
                    str(source_path).encode('utf-8'),
                    str(expected_output).encode('utf-8')
                )
                
                assert result == expected_output
    
    def test_convert_failure_no_output(self):
        """Test conversion failure when output file not created"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            with tempfile.TemporaryDirectory() as tmpdir:
                source_path = Path(tmpdir) / "test.trc"
                source_path.touch()
                
                # Mock conversion that doesn't create output file
                self.mock_wrapper.convert_file.side_effect = lambda src, dst: None
                
                # Should raise RuntimeError
                with pytest.raises(RuntimeError, match="output file not created"):
                    converter.convert(source_path, Path(tmpdir))
    
    def test_convert_exception_handling(self):
        """Test conversion handles PyEEGFormat exceptions"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            with tempfile.TemporaryDirectory() as tmpdir:
                source_path = Path(tmpdir) / "test.trc"
                source_path.touch()
                
                # Mock conversion that raises exception
                self.mock_wrapper.convert_file.side_effect = Exception("Conversion error")
                
                # Should raise RuntimeError with original message
                with pytest.raises(RuntimeError, match="Failed to convert.*Conversion error"):
                    converter.convert(source_path, Path(tmpdir))
    
    def test_extract_metadata_full(self):
        """Test complete metadata extraction from TRC file"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            with tempfile.NamedTemporaryFile(suffix='.trc', delete=False) as tmp:
                tmp_path = Path(tmp.name)
                
            try:
                metadata = converter.extract_metadata(tmp_path)
                
                # Verify basic metadata
                assert metadata['SamplingFrequency'] == 512.0
                assert metadata['RecordingDuration'] == 1000.0  # 512000 / 512
                assert metadata['RecordingType'] == 'continuous'
                assert metadata['Manufacturer'] == 'Micromed'
                assert metadata['PowerLineFrequency'] == 50
                assert metadata['EEGChannelCount'] == 64
                
                # Verify hardware filters extracted
                assert 'HardwareFilters' in metadata
                assert metadata['HardwareFilters']['HighpassFilter']['Frequency'] == 0.5
                assert metadata['HardwareFilters']['LowpassFilter']['Frequency'] == 70.0
                
                # Verify reference extracted
                assert metadata['EEGReference'] == 'REF'
                
            finally:
                tmp_path.unlink()
    
    def test_extract_metadata_minimal_on_error(self):
        """Test metadata extraction returns minimal data on error"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            # Make PyIFile raise exception
            self.mock_wrapper.PyIFile.side_effect = Exception("Cannot open file")
            
            with tempfile.NamedTemporaryFile(suffix='.trc', delete=False) as tmp:
                tmp_path = Path(tmp.name)
                
            try:
                metadata = converter.extract_metadata(tmp_path)
                
                # Should return minimal metadata
                assert metadata['Manufacturer'] == 'Micromed'
                assert metadata['PowerLineFrequency'] == 50
                assert metadata['RecordingType'] == 'continuous'
                assert len(metadata) == 3  # Only minimal fields
                
            finally:
                tmp_path.unlink()
    
    def test_extract_hardware_filters_none(self):
        """Test hardware filter extraction when no filters present"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            # Mock electrode with no filters
            mock_electrode_no_filter = MagicMock()
            mock_electrode_no_filter.PrefilteringHighPassLimit.return_value = 0
            mock_electrode_no_filter.PrefilteringLowPassLimit.return_value = 0
            
            mock_file_no_filter = MagicMock()
            mock_file_no_filter.get_electrode_count.return_value = 1
            mock_file_no_filter.get_electrode.return_value = mock_electrode_no_filter
            
            result = converter._extract_hardware_filters(mock_file_no_filter)
            assert result is None
    
    def test_extract_reference_mixed(self):
        """Test reference extraction with mixed references"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            # Mock electrodes with different references
            electrodes = []
            for i, ref in enumerate([b'REF1', b'REF2', b'REF1', b'REF3']):
                mock_elec = MagicMock()
                mock_elec.ReferenceLabel.return_value = ref
                electrodes.append(mock_elec)
            
            mock_file_mixed = MagicMock()
            mock_file_mixed.get_electrode_count.return_value = len(electrodes)
            mock_file_mixed.get_electrode.side_effect = lambda i: electrodes[i]
            
            result = converter._extract_reference_info(mock_file_mixed)
            assert result == "mixed"
    
    def test_extract_reference_single(self):
        """Test reference extraction with single reference"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            # Mock electrodes with same reference
            mock_elec = MagicMock()
            mock_elec.ReferenceLabel.return_value = b'COMMON_REF'
            
            mock_file_single = MagicMock()
            mock_file_single.get_electrode_count.return_value = 5
            mock_file_single.get_electrode.return_value = mock_elec
            
            result = converter._extract_reference_info(mock_file_single)
            assert result == "COMMON_REF"


# Integration test that can be run with actual TRC file
class TestTrcToEdfIntegration:
    """Integration tests with actual TRC files (if available)"""
    
    @pytest.mark.skipif(
        not Path("/tmp/test.trc").exists(),
        reason="No test TRC file available at /tmp/test.trc"
    )
    def test_real_trc_conversion(self):
        """Test with real TRC file if available"""
        converter = TrcToEdfConverterPyEEG()
        
        test_file = Path("/tmp/test.trc")
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Test conversion
            result = converter.convert(test_file, output_dir)
            assert result.exists()
            assert result.suffix == '.edf'
            
            # Test metadata extraction
            metadata = converter.extract_metadata(test_file)
            assert 'SamplingFrequency' in metadata
            assert 'Manufacturer' in metadata
            
            # Verify output is valid EDF (basic check)
            assert result.stat().st_size > 0
            
            # Could add more validation with mne or pyedflib
            # e.g., verify the EDF can be read back


if __name__ == "__main__":
    pytest.main([__file__, "-v"])