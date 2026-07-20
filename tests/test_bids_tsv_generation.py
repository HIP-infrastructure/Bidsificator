#!/usr/bin/env python
"""
Comprehensive tests for BIDS TSV generation system

Tests the complete schema-driven pipeline from file metadata extraction
to BIDS-compliant TSV file generation.
"""

import os
import tempfile
from pathlib import Path
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from bidsificator.core.schema.tsv_schema_mapper import BidsSchemaMapper, ColumnDefinition
from bidsificator.services.BidsMetadataExtractorService import BidsMetadataExtractor
from bidsificator.converters.trc_to_edf_pyeeg import TrcToEdfConverterPyEEG

# Optional real-TRC integration test. Set BIDSIFICATOR_TRC_TEST_FILE to a .TRC
# file path to run it; otherwise it is skipped (no hardcoded personal paths).
TRC_TEST_FILE = os.environ.get("BIDSIFICATOR_TRC_TEST_FILE")


class TestBidsSchemaMapper:
    """Test BIDS schema mapping for TSV files"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mapper = BidsSchemaMapper()
    
    def test_get_channels_requirements_ieeg(self):
        """Test channel requirements for iEEG data"""
        requirements = self.mapper.get_tsv_column_requirements('channels', 'ieeg')
        
        # Verify core required columns are present
        assert 'name' in requirements
        assert 'type' in requirements
        assert requirements['name'].name == 'name'
        assert requirements['name'].data_type == 'string'
        
        # Verify iEEG-specific columns
        assert 'reference' in requirements
        assert 'group' in requirements
        
        print(f"✅ Found {len(requirements)} channel requirements for iEEG")
        for name, req in requirements.items():
            print(f"   - {name}: {req.data_type} ({req.requirement_level})")
    
    def test_get_events_requirements(self):
        """Test event requirements"""
        requirements = self.mapper.get_tsv_column_requirements('events')
        
        # Verify core columns
        assert 'onset' in requirements
        assert 'duration' in requirements
        assert requirements['onset'].data_type == 'number'
        assert requirements['duration'].data_type == 'number'
        
        print(f"✅ Found {len(requirements)} event requirements")
        for name, req in requirements.items():
            print(f"   - {name}: {req.data_type} ({req.requirement_level})")
    
    def test_validate_valid_channels_dataframe(self):
        """Test validation of valid channels DataFrame"""
        # Create valid channels DataFrame
        channels_df = pd.DataFrame({
            'name': ['A\'1', 'A\'2', 'B\'1'],
            'type': ['SEEG', 'SEEG', 'SEEG'],
            'units': ['µV', 'µV', 'µV'],
            'sampling_frequency': [1024.0, 1024.0, 1024.0],
            'status': ['good', 'good', 'good']
        })
        
        errors = self.mapper.validate_tsv_dataframe(channels_df, 'channels', 'ieeg')
        assert len(errors) == 0, f"Should be valid but got errors: {errors}"
        print("✅ Valid channels DataFrame passes validation")
    
    def test_validate_invalid_channels_dataframe(self):
        """Test validation catches invalid channels DataFrame"""
        # Create invalid DataFrame (missing required column)
        channels_df = pd.DataFrame({
            'type': ['SEEG', 'SEEG'],
            'units': ['µV', 'µV']
            # Missing 'name' column
        })
        
        errors = self.mapper.validate_tsv_dataframe(channels_df, 'channels', 'ieeg')
        assert len(errors) > 0, "Should have validation errors"
        assert any('name' in error for error in errors), "Should mention missing name column"
        print(f"✅ Invalid channels DataFrame caught {len(errors)} errors")
    
    def test_create_compliant_dataframe(self):
        """Test creation of BIDS-compliant DataFrame from raw data"""
        raw_data = [
            {
                'name': 'A\'1',
                'type': 'SEEG', 
                'units': 'µV',
                'sampling_frequency': 1024.0,
                'custom_field': 'should_be_preserved'
            },
            {
                'name': 'A\'2',
                'type': 'SEEG',
                'units': 'µV'
                # Missing sampling_frequency - should get default
            }
        ]
        
        df = self.mapper.create_compliant_dataframe(raw_data, 'channels', 'ieeg')
        
        # Verify structure
        assert len(df) == 2
        assert 'name' in df.columns
        assert 'sampling_frequency' in df.columns
        assert 'reference' in df.columns  # recommended column auto-added for iEEG channels
        
        # Verify data integrity
        assert df.loc[0, 'name'] == 'A\'1'
        assert df.loc[0, 'sampling_frequency'] == 1024.0
        # A value missing from a single row (vs a wholly-absent column) is left
        # as NaN — written as an empty field in the TSV. It is NOT coerced to 0,
        # which would be a wrong sampling frequency rather than "missing".
        assert pd.isna(df.loc[1, 'sampling_frequency'])
        
        print(f"✅ Created compliant DataFrame with {len(df.columns)} columns")


class TestTrcMetadataExtraction:
    """Test TRC file metadata extraction"""
    
    def setup_method(self):
        """Set up test fixtures with mocked PyEEGFormat"""
        self.mock_wrapper = MagicMock()
        
        # Mock PyIFile object
        self.mock_file = MagicMock()
        self.mock_file.get_sampling_frequency.return_value = 1024.0
        self.mock_file.get_electrode_count.return_value = 3
        self.mock_file.get_trigger_count.return_value = 2
        self.mock_file.get_note_count.return_value = 1
        
        # Mock electrodes
        self.mock_electrodes = []
        for i, name in enumerate(['A\'1', 'A\'2', 'B\'1']):
            mock_electrode = MagicMock()
            mock_electrode.Label.return_value = name.encode('utf-8')
            mock_electrode.Unit.return_value = b'uV'
            mock_electrode.PrefilteringHighPassLimit.return_value = 0.5
            mock_electrode.PrefilteringLowPassLimit.return_value = 70.0
            mock_electrode.ReferenceLabel.return_value = b'REF'
            self.mock_electrodes.append(mock_electrode)
        
        self.mock_file.get_electrode.side_effect = lambda i: self.mock_electrodes[i]
        
        # Mock triggers
        self.mock_triggers = []
        for i, (sample, code) in enumerate([(1000, 1), (2000, 2)]):
            mock_trigger = MagicMock()
            mock_trigger.Sample.return_value = sample
            mock_trigger.Code.return_value = code
            self.mock_triggers.append(mock_trigger)
        
        self.mock_file.get_trigger.side_effect = lambda i: self.mock_triggers[i]
        
        # Mock notes
        mock_note = MagicMock()
        mock_note.Sample.return_value = 1500
        mock_note.Description.return_value = b'Test annotation'
        self.mock_file.get_note.return_value = mock_note
        
        # Configure wrapper
        self.mock_wrapper.PyIFile.return_value = self.mock_file
    
    def test_extract_channels_data_success(self):
        """Test successful channel data extraction from TRC"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            # Create temporary TRC file
            with tempfile.NamedTemporaryFile(suffix='.trc', delete=False) as tmp:
                tmp_path = Path(tmp.name)
            
            try:
                channels_data = converter.extract_channels_data(tmp_path)
                
                # Verify extraction results
                assert len(channels_data) == 3, "Should extract 3 channels"
                
                # Verify first channel
                ch1 = channels_data[0]
                assert ch1['name'] == 'A\'1'
                assert ch1['type'] == 'SEEG'
                assert ch1['units'] == 'uV'
                assert ch1['sampling_frequency'] == 1024.0
                assert ch1['group'] == 'A'  # Parsed from A'1
                assert ch1['reference'] == 'REF'
                
                print(f"✅ Successfully extracted {len(channels_data)} channels")
                print(f"   Sample channel: {ch1['name']} ({ch1['type']}, {ch1['units']})")
                
            finally:
                tmp_path.unlink()
    
    def test_extract_events_data_success(self):
        """Test successful event data extraction from TRC"""
        with patch.object(TrcToEdfConverterPyEEG, '_import_platform_wrapper', return_value=self.mock_wrapper):
            converter = TrcToEdfConverterPyEEG()
            
            with tempfile.NamedTemporaryFile(suffix='.trc', delete=False) as tmp:
                tmp_path = Path(tmp.name)
            
            try:
                events_data = converter.extract_events_data(tmp_path)
                
                # Should have 2 triggers + 1 note = 3 events
                assert len(events_data) == 3, f"Should extract 3 events, got {len(events_data)}"
                
                # Events should be sorted by onset time
                onsets = [event['onset'] for event in events_data]
                assert onsets == sorted(onsets), "Events should be sorted by onset time"
                
                # Check first trigger. Triggers use a generic trial_type; the
                # trigger code is carried in the BIDS 'value' column.
                trigger1 = events_data[0]  # Sample 1000
                assert trigger1['onset'] == 1000/1024.0
                assert trigger1['trial_type'] == 'trigger'
                assert trigger1['value'] == '1'

                # Check annotation. Note text becomes the trial_type.
                annotation = next(e for e in events_data if e['trial_type'] == 'Test annotation')
                assert annotation['onset'] == 1500/1024.0

                print(f"✅ Successfully extracted {len(events_data)} events")
                print(f"   Triggers: {len([e for e in events_data if e['trial_type'] == 'trigger'])}")
                print(f"   Annotations: {len([e for e in events_data if e['trial_type'] != 'trigger'])}")
                
            finally:
                tmp_path.unlink()


class TestBidsMetadataExtractor:
    """Test the complete metadata extraction service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.extractor = BidsMetadataExtractor()
    
    def test_extract_channels_tsv_with_trc(self):
        """Test channels TSV extraction from TRC file"""
        # Mock the converter registry to return our TRC converter
        mock_converter = MagicMock()
        mock_converter.extract_channels_data.return_value = [
            {
                'name': 'A\'1',
                'type': 'SEEG',
                'units': 'µV',
                'sampling_frequency': 1024.0,
                'status': 'good',
                'group': 'A',
                'reference': 'REF'
            },
            {
                'name': 'B\'1', 
                'type': 'SEEG',
                'units': 'µV',
                'sampling_frequency': 1024.0,
                'status': 'good',
                'group': 'B',
                'reference': 'REF'
            }
        ]
        
        with patch.object(self.extractor.converter_registry, 'get_converter', return_value=mock_converter):
            test_path = Path('/fake/path/test.trc')
            
            channels_df = self.extractor.extract_channels_tsv(test_path, 'ieeg')
            
            # Verify DataFrame structure
            assert len(channels_df) == 2
            assert 'name' in channels_df.columns
            assert 'type' in channels_df.columns
            assert channels_df.loc[0, 'name'] == 'A\'1'
            assert channels_df.loc[1, 'name'] == 'B\'1'
            
            print(f"✅ Generated channels.tsv with {len(channels_df)} rows and {len(channels_df.columns)} columns")
    
    def test_extract_events_tsv_with_trc(self):
        """Test events TSV extraction from TRC file"""
        mock_converter = MagicMock()
        mock_converter.extract_events_data.return_value = [
            {
                'onset': 0.976,  # 1000/1024
                'duration': 0.0,
                'trial_type': 'trigger_1',
                'value': '1',
                'response_time': 'n/a',
                'stim_file': 'n/a'
            },
            {
                'onset': 1.465,  # 1500/1024  
                'duration': 'n/a',
                'trial_type': 'annotation',
                'value': 'Test note',
                'response_time': 'n/a',
                'stim_file': 'n/a'
            }
        ]
        
        with patch.object(self.extractor.converter_registry, 'get_converter', return_value=mock_converter):
            test_path = Path('/fake/path/test.trc')
            
            events_df = self.extractor.extract_events_tsv(test_path, 'ieeg')
            
            # Verify DataFrame structure
            assert len(events_df) == 2
            assert 'onset' in events_df.columns
            assert 'duration' in events_df.columns
            assert events_df.loc[0, 'onset'] == 0.976
            assert events_df.loc[1, 'trial_type'] == 'annotation'
            
            print(f"✅ Generated events.tsv with {len(events_df)} rows and {len(events_df.columns)} columns")
    
    def test_validation_integration(self):
        """Test that generated TSV files pass BIDS validation"""
        # Create test data that should be valid
        channels_data = [
            {
                'name': 'A\'1',
                'type': 'SEEG',
                'units': 'µV',
                'sampling_frequency': 1024.0,
                'status': 'good'
            }
        ]
        
        channels_df = self.extractor.schema_mapper.create_compliant_dataframe(
            channels_data, 'channels', 'ieeg'
        )
        
        is_valid, errors = self.extractor.validate_generated_tsv(channels_df, 'channels', 'ieeg')
        
        assert is_valid, f"Generated channels.tsv should be valid, but got errors: {errors}"
        print("✅ Generated TSV passes BIDS schema validation")


class TestIntegrationWithRealTrcFile:
    """Integration test with real TRC file"""
    
    @pytest.mark.skipif(
        not TRC_TEST_FILE,
        reason="Set BIDSIFICATOR_TRC_TEST_FILE to run this integration test",
    )
    def test_real_trc_metadata_extraction(self):
        """Test metadata extraction with real TRC file"""
        real_trc = Path(TRC_TEST_FILE)
        if not real_trc.exists():
            pytest.skip(f"BIDSIFICATOR_TRC_TEST_FILE not found: {real_trc}")

        extractor = BidsMetadataExtractor()
        
        print(f"\\n=== Testing with real TRC file: {real_trc.name} ===")
        
        # Test channels extraction
        channels_df = extractor.extract_channels_tsv(real_trc, 'ieeg')
        print(f"Extracted {len(channels_df)} channels")
        
        # Verify some channels have real names (not CH001, CH002...)
        channel_names = channels_df['name'].tolist()
        real_names = [name for name in channel_names if not name.startswith('CH')]
        print(f"Real channel names found: {len(real_names)}/{len(channel_names)}")
        if real_names:
            print(f"Sample real names: {real_names[:5]}")
        
        # Test events extraction
        events_df = extractor.extract_events_tsv(real_trc, 'ieeg')
        print(f"Extracted {len(events_df)} events")
        
        if len(events_df) > 0:
            print(f"Event types: {events_df['trial_type'].value_counts().to_dict()}")
            print(f"Time range: {events_df['onset'].min():.3f}s - {events_df['onset'].max():.3f}s")
        
        # Test validation
        channels_valid, channels_errors = extractor.validate_generated_tsv(channels_df, 'channels', 'ieeg')
        events_valid, events_errors = extractor.validate_generated_tsv(events_df, 'events', 'ieeg')
        
        print(f"\\nValidation results:")
        print(f"Channels valid: {channels_valid} (errors: {len(channels_errors)})")
        print(f"Events valid: {events_valid} (errors: {len(events_errors)})")
        
        if channels_errors:
            print(f"Channel errors: {channels_errors}")
        if events_errors:
            print(f"Event errors: {events_errors}")
        
        # Save test files for inspection
        with tempfile.TemporaryDirectory() as tmpdir:
            channels_path = Path(tmpdir) / 'test_channels.tsv'
            events_path = Path(tmpdir) / 'test_events.tsv'
            
            channels_df.to_csv(channels_path, sep='\t', index=False)
            events_df.to_csv(events_path, sep='\t', index=False)

            print("\nGenerated test files:")
            print(f"  {channels_path} ({channels_path.stat().st_size} bytes)")
            print(f"  {events_path} ({events_path.stat().st_size} bytes)")
        
        print("✅ Real TRC file metadata extraction completed")


def main():
    """Run all tests"""
    print("=" * 80)
    print("COMPREHENSIVE BIDS TSV GENERATION TESTS")
    print("=" * 80)
    
    test_classes = [
        TestBidsSchemaMapper,
        TestTrcMetadataExtraction,
        TestBidsMetadataExtractor,
        TestIntegrationWithRealTrcFile
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\\n--- {test_class.__name__} ---")
        
        instance = test_class()
        test_methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                # Set up
                if hasattr(instance, 'setup_method'):
                    instance.setup_method()
                
                # Run test
                method = getattr(instance, method_name)
                method()
                
                passed_tests += 1
                print(f"✅ {method_name}")
                
            except Exception as e:
                print(f"❌ {method_name}: {e}")
    
    print(f"\\n{'='*80}")
    print(f"TEST RESULTS: {passed_tests}/{total_tests} passed")
    print(f"{'='*80}")
    
    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())