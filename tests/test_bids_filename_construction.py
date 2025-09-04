#!/usr/bin/env python
"""
Test BIDS filename construction and TSV generation
Tests the fix for proper BIDS filename generation without duplicate suffixes
"""

import tempfile
from pathlib import Path

from bidsificator.core.schema import BidsSchemaManager
from bidsificator.core.BidsSubjectSchema import BidsSubject


class TestBidsFilenameConstruction:
    """Test proper BIDS filename construction for data and TSV files"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.schema_manager = BidsSchemaManager.get_instance()
    
    def test_build_bids_filename_method(self):
        """Test the _build_bids_filename method directly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            subject = BidsSubject('testsubject', temp_path, self.schema_manager)
            
            entities = {'sub': 'testsubject', 'ses': '01', 'task': 'test', 'acq': '01'}
            
            # Test different suffix types
            ieeg_filename = subject._build_bids_filename(entities, 'ieeg', '.edf')
            channels_filename = subject._build_bids_filename(entities, 'channels', '.tsv')
            events_filename = subject._build_bids_filename(entities, 'events', '.tsv')
            electrodes_filename = subject._build_bids_filename(entities, 'electrodes', '.tsv')
            coordsystem_filename = subject._build_bids_filename(entities, 'coordsystem', '.json')
            
            # Verify proper construction
            assert ieeg_filename == 'sub-testsubject_ses-01_task-test_acq-01_ieeg.edf'
            assert channels_filename == 'sub-testsubject_ses-01_task-test_acq-01_channels.tsv'
            assert events_filename == 'sub-testsubject_ses-01_task-test_acq-01_events.tsv'
            assert electrodes_filename == 'sub-testsubject_ses-01_task-test_acq-01_electrodes.tsv'
            assert coordsystem_filename == 'sub-testsubject_ses-01_task-test_acq-01_coordsystem.json'
            
            # Verify no duplicate suffixes
            assert '_ieeg_channels' not in channels_filename
            assert '_ieeg_events' not in events_filename
            assert '_ieeg_electrodes' not in electrodes_filename
    
    def test_tsv_filename_generation_integration(self):
        """Test end-to-end TSV filename generation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            subject = BidsSubject('testsubject', temp_path, self.schema_manager)
            
            # Create directory structure
            test_data_dir = temp_path / 'sub-testsubject' / 'ses-01' / 'ieeg'
            test_data_dir.mkdir(parents=True)
            
            # Create a dummy data file
            test_data_path = test_data_dir / 'sub-testsubject_ses-01_task-test_acq-01_ieeg.edf'
            test_data_path.write_text('dummy data file')
            
            entities = {'sub': 'testsubject', 'ses': '01', 'task': 'test', 'acq': '01'}
            
            # Generate TSV files using the clean architecture
            subject._generate_ephys_files(test_data_path, entities, 'ieeg')
            
            # Verify correct filenames were created
            expected_channels = test_data_dir / 'sub-testsubject_ses-01_task-test_acq-01_channels.tsv'
            expected_events = test_data_dir / 'sub-testsubject_ses-01_task-test_acq-01_events.tsv'
            expected_electrodes = test_data_dir / 'sub-testsubject_ses-01_task-test_acq-01_electrodes.tsv'
            expected_coordsystem = test_data_dir / 'sub-testsubject_ses-01_task-test_acq-01_coordsystem.json'
            
            assert expected_channels.exists()
            assert expected_events.exists()
            assert expected_electrodes.exists()  # Required for iEEG data
            assert expected_coordsystem.exists()  # Required when electrodes.tsv is present
            
            # Verify no files with duplicate suffixes were created
            bad_channels = test_data_dir / 'sub-testsubject_ses-01_task-test_acq-01_ieeg_channels.tsv'
            bad_events = test_data_dir / 'sub-testsubject_ses-01_task-test_acq-01_ieeg_events.tsv'
            bad_electrodes = test_data_dir / 'sub-testsubject_ses-01_task-test_acq-01_ieeg_electrodes.tsv'
            
            assert not bad_channels.exists()
            assert not bad_events.exists()
            assert not bad_electrodes.exists()
    
    def test_bids_validator_compliance(self):
        """Test that generated filenames match BIDS validator expectations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            subject = BidsSubject('testsubject', temp_path, self.schema_manager)
            
            entities = {
                'sub': 'finaltest',
                'ses': 'post', 
                'task': 'Cognitiv',
                'acq': '01'
            }
            
            # Test the exact case from the BIDS validator error
            channels_filename = subject._build_bids_filename(entities, 'channels', '.tsv')
            events_filename = subject._build_bids_filename(entities, 'events', '.tsv')
            
            # These should match BIDS validator expectations exactly
            expected_channels = 'sub-finaltest_ses-post_task-Cognitiv_acq-01_channels.tsv'
            expected_events = 'sub-finaltest_ses-post_task-Cognitiv_acq-01_events.tsv'
            
            assert channels_filename == expected_channels
            assert events_filename == expected_events
    
    def test_multiple_datatypes(self):
        """Test filename construction for different datatypes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            subject = BidsSubject('testsubject', temp_path, self.schema_manager)
            
            entities = {'sub': 'testsubject', 'task': 'rest'}
            
            # Test different electrophysiology datatypes
            for datatype in ['ieeg', 'eeg', 'meg']:
                data_filename = subject._build_bids_filename(entities, datatype, '.edf')
                channels_filename = subject._build_bids_filename(entities, 'channels', '.tsv')
                events_filename = subject._build_bids_filename(entities, 'events', '.tsv')
                
                # Verify data file has datatype suffix
                assert f'_{datatype}.' in data_filename
                
                # Verify TSV files don't have datatype suffix
                assert f'_{datatype}_channels' not in channels_filename
                assert f'_{datatype}_events' not in events_filename
                
                # Verify TSV files have proper suffix
                assert channels_filename.endswith('_channels.tsv')
                assert events_filename.endswith('_events.tsv')


def test_filename_construction():
    """Run all filename construction tests"""
    test_class = TestBidsFilenameConstruction()
    test_class.setup_method()
    
    print("🧪 Testing BIDS filename construction...")
    
    test_class.test_build_bids_filename_method()
    print("✅ _build_bids_filename method test passed")
    
    test_class.test_tsv_filename_generation_integration()
    print("✅ TSV filename generation integration test passed")
    
    test_class.test_bids_validator_compliance()
    print("✅ BIDS validator compliance test passed")
    
    test_class.test_multiple_datatypes()
    print("✅ Multiple datatypes test passed")
    
    print("🎯 All filename construction tests passed!")


if __name__ == "__main__":
    test_filename_construction()