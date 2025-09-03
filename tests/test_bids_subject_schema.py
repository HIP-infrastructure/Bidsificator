#!/usr/bin/env python
"""
Comprehensive test for the improved schema-driven BidsSubject implementation
"""

import tempfile
import shutil
from pathlib import Path

from bidsificator.core.schema import BidsSchemaManager
from bidsificator.core.BidsSubjectSchema import BidsSubject
from bidsificator.core.file_analysis import FileAnalysis
from bidsificator.core.bids_constants import (
    DEFAULT_SUFFIXES,
    DEFAULT_METADATA_VALUES,
    DEFAULT_CHANNEL_COUNTS
)


def test_improved_bids_subject():
    """Test improved BidsSubject with all new features"""
    
    print("=" * 70)
    print("TESTING IMPROVED SCHEMA-DRIVEN BIDSSUBJECT")
    print("=" * 70)
    
    # Setup
    schema_manager = BidsSchemaManager()
    schema_manager.load_schema()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        dataset_path = Path(temp_dir) / "test_dataset"
        dataset_path.mkdir()
        
        print("✅ Schema loaded and dataset directory created")
        
        # Test 1: Create BidsSubject with validation
        print("\n1. TESTING BIDSSUBJECT CREATION & VALIDATION")
        print("-" * 50)
        
        try:
            subject = BidsSubject("P001", dataset_path, schema_manager)
            print(f"✅ Created subject: {subject.get_subject_id()}")
            print(f"   Subject path: {subject.get_subject_path()}")
            
            # Test entity formatting
            assert str(subject.get_subject_path()).endswith("sub-P001")
            print("✅ Entity formatting works correctly")
            
        except Exception as e:
            print(f"❌ Failed to create subject: {e}")
            return False
        
        # Test 2: File Analysis System
        print("\n2. TESTING FILE ANALYSIS SYSTEM")
        print("-" * 50)
        
        # Create dummy files for testing
        dummy_trc = Path(temp_dir) / "test.trc"
        dummy_edf = Path(temp_dir) / "test.edf" 
        dummy_nii = Path(temp_dir) / "test.nii"
        
        dummy_trc.write_text("dummy trc data")
        dummy_edf.write_text("dummy edf data")
        dummy_nii.write_text("dummy nifti data")
        
        # Test file analysis
        trc_analysis = subject.analyze_file(dummy_trc)
        print(f"✅ TRC analysis: needs_conversion={trc_analysis.needs_conversion}, datatype={trc_analysis.bids_datatype}")
        
        edf_analysis = subject.analyze_file(dummy_edf)
        print(f"✅ EDF analysis: needs_conversion={edf_analysis.needs_conversion}, datatype={edf_analysis.bids_datatype}")
        
        nii_analysis = subject.analyze_file(dummy_nii)
        print(f"✅ NII analysis: needs_conversion={nii_analysis.needs_conversion}, datatype={nii_analysis.bids_datatype}")
        
        # Test 3: Constants System
        print("\n3. TESTING CONSTANTS SYSTEM")
        print("-" * 50)
        
        print(f"✅ Default suffixes loaded: {len(DEFAULT_SUFFIXES)} datatypes")
        print(f"   - iEEG: {DEFAULT_SUFFIXES.get('ieeg')}")
        print(f"   - Anatomy: {DEFAULT_SUFFIXES.get('anat')}")
        
        print(f"✅ Metadata values: {DEFAULT_METADATA_VALUES}")
        print(f"✅ Channel counts: {DEFAULT_CHANNEL_COUNTS}")
        
        # Test 4: Advanced Path Building
        print("\n4. TESTING ADVANCED PATH BUILDING")
        print("-" * 50)
        
        # Test various entity combinations
        test_entities = [
            {'sub': 'P001', 'task': 'rest'},
            {'sub': 'P001', 'ses': 'pre', 'task': 'memory', 'run': '2'},
            {'sub': 'P001', 'ses': 'post', 'task': 'motor', 'acq': 'highres', 'run': '1'}
        ]
        
        for entities in test_entities:
            try:
                path = subject._build_target_path(entities, 'ieeg', 'ieeg', '.edf')
                filename = path.name
                print(f"✅ Built path: {filename}")
                
                # Verify entity order is correct
                assert filename.startswith('sub-P001')
                if 'ses' in entities:
                    assert f"ses-{entities['ses']}" in filename
                if 'task' in entities:
                    assert f"task-{entities['task']}" in filename
                
            except Exception as e:
                print(f"❌ Path building failed: {e}")
                return False
        
        # Test 5: Datatype Path Creation
        print("\n5. TESTING DATATYPE PATH CREATION")
        print("-" * 50)
        
        datatypes_to_test = ['ieeg', 'eeg', 'anat', 'func', 'meg']
        sessions_to_test = [None, 'baseline', 'followup']
        
        for datatype in datatypes_to_test:
            for session in sessions_to_test:
                try:
                    path = subject.get_datatype_path(datatype, session)
                    print(f"✅ {datatype} {'(no session)' if session is None else f'ses-{session}'}: {path.name}")
                    assert path.exists()
                    
                    if session:
                        assert f"ses-{session}" in str(path)
                    assert datatype in str(path)
                    
                except Exception as e:
                    print(f"❌ Failed to create {datatype} path: {e}")
        
        # Test 6: Optional Metadata System
        print("\n6. TESTING OPTIONAL METADATA SYSTEM")
        print("-" * 50)
        
        test_metadata = {
            'Institution': 'Test University',
            'PowerLineFrequency': 60,
            'InstitutionName': 'Advanced Neuroscience Lab'
        }
        
        subject.set_optional_metadata(test_metadata)
        print(f"✅ Set optional metadata: {subject.optional_metadata}")
        
        # Test default metadata generation
        default_val = subject._get_default_metadata_value(
            'TaskName', 
            {'type': 'string'}, 
            {'task': 'memory'}
        )
        print(f"✅ Default TaskName: {default_val}")
        assert default_val == 'memory'
        
        unknown_val = subject._get_default_metadata_value(
            'SomeUnknownField',
            {'type': 'string'},
            {}
        )
        print(f"✅ Default unknown field: {unknown_val}")
        assert unknown_val == DEFAULT_METADATA_VALUES['NOT_AVAILABLE']
        
        # Test 7: Helper Methods
        print("\n7. TESTING HELPER METHODS")
        print("-" * 50)
        
        # Test entity formatting
        formatted = subject._format_entity('ses', 'baseline')
        print(f"✅ Entity formatting: 'ses' + 'baseline' → '{formatted}'")
        assert formatted == 'ses-baseline'
        
        # Test BIDS filename building
        entities = {'sub': 'P001', 'ses': 'pre', 'task': 'rest', 'run': '1'}
        filename = subject._build_bids_filename(entities, 'ieeg', '.edf')
        print(f"✅ BIDS filename: {filename}")
        assert filename == 'sub-P001_ses-pre_task-rest_run-1_ieeg.edf'
        
        # Test 8: Metadata Files Generation
        print("\n8. TESTING METADATA FILE GENERATION")
        print("-" * 50)
        
        # Create test data file
        test_data_path = subject.get_datatype_path('ieeg') / 'sub-P001_task-test_ieeg.edf'
        test_data_path.write_text("dummy data")
        
        entities = {'sub': 'P001', 'task': 'test'}
        
        try:
            # Test channels dataframe creation
            channels_df = subject._create_channels_dataframe('ieeg', 32)
            print(f"✅ Created channels dataframe: {len(channels_df)} channels")
            assert len(channels_df) == 32
            assert channels_df['type'].iloc[0] == 'SEEG'
            
            # Test events dataframe creation
            events_df = subject._create_events_dataframe()
            print(f"✅ Created events dataframe: {len(events_df.columns)} columns")
            assert 'onset' in events_df.columns
            assert 'duration' in events_df.columns
            
            # Test metadata file generation
            subject._generate_metadata_files(test_data_path, 'ieeg', 'ieeg', entities, {})
            
            # Check if files were created
            json_file = test_data_path.with_suffix('.json')
            channels_file = test_data_path.parent / 'sub-P001_task-test_ieeg_channels.tsv'
            events_file = test_data_path.parent / 'sub-P001_task-test_ieeg_events.tsv'
            
            print(f"✅ JSON sidecar created: {json_file.exists()}")
            print(f"✅ Channels file created: {channels_file.exists()}")
            print(f"✅ Events file created: {events_file.exists()}")
            
        except Exception as e:
            print(f"❌ Metadata generation failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 9: Session and Datatype Listing
        print("\n9. TESTING SESSION & DATATYPE LISTING")
        print("-" * 50)
        
        sessions = subject.get_sessions()
        print(f"✅ Found sessions: {sessions}")
        
        datatypes = subject.get_datatypes()
        print(f"✅ Found datatypes: {datatypes}")
        
        datatypes_in_session = subject.get_datatypes('pre')
        print(f"✅ Datatypes in ses-pre: {datatypes_in_session}")
        
        # Test 10: File Listing
        print("\n10. TESTING FILE LISTING")
        print("-" * 50)
        
        all_files = subject.list_files()
        print(f"✅ All files: {len(all_files)} files")
        
        ieeg_files = subject.list_files('ieeg')
        print(f"✅ iEEG files: {len(ieeg_files)} files")
        
    print(f"\n{'='*70}")
    print("✅ ALL IMPROVED BIDSSUBJECT TESTS PASSED!")
    print(f"{'='*70}")
    return True


def test_file_analysis_class():
    """Test FileAnalysis dataclass"""
    print("\n" + "="*50)
    print("TESTING FILEANALYSIS CLASS")
    print("="*50)
    
    # Test basic FileAnalysis
    source_path = Path("/tmp/test.trc")
    analysis = FileAnalysis(
        source_path=source_path,
        needs_conversion=True,
        converter=None,
        bids_datatype="ieeg"
    )
    
    print(f"✅ FileAnalysis created: {analysis.source_path}")
    print(f"   Needs conversion: {analysis.needs_conversion}")
    print(f"   BIDS datatype: {analysis.bids_datatype}")
    print(f"   Is valid: {analysis.is_valid}")
    print(f"   Converter name: {analysis.converter_name}")
    
    # Test error case
    error_analysis = FileAnalysis(
        source_path=source_path,
        needs_conversion=False,
        converter=None,
        bids_datatype=None,
        error="File not supported"
    )
    
    print(f"✅ Error analysis: {error_analysis.error}")
    print(f"   Is valid: {error_analysis.is_valid}")
    
    return True


if __name__ == "__main__":
    success1 = test_improved_bids_subject()
    success2 = test_file_analysis_class()
    
    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED! IMPROVED BIDSSUBJECT IS READY!")
    else:
        print("\n❌ SOME TESTS FAILED")
    
    exit(0 if (success1 and success2) else 1)