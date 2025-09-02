#!/usr/bin/env python3
"""
Test script for BIDS schema parsing
"""

import sys
sys.path.insert(0, '.')

from bidsificator.core.schema import BidsSchemaManager

def test_schema_loading():
    """Test basic schema loading and parsing"""
    print("Testing BIDS schema loading...")
    
    try:
        # Create schema manager
        manager = BidsSchemaManager()
        
        # Load schema
        print("Loading schema...")
        manager.load_schema()
        
        # Test basic info
        print(f"BIDS Version: {manager.get_bids_version()}")
        print(f"Schema Version: {manager.get_schema_version()}")
        
        # Test entities
        print(f"\nFound {len(manager.entities)} entities:")
        for name, entity in list(manager.entities.items())[:10]:  # Show first 10
            print(f"  - {name}: {entity.format.value} format, pattern: {entity.pattern}")
        
        # Test datatypes
        print(f"\nFound {len(manager.datatypes)} datatypes:")
        for name in manager.datatypes:
            print(f"  - {name}")
        
        # Test specific datatype
        ieeg = manager.get_datatype('ieeg')
        if ieeg:
            print(f"\niEEG datatype:")
            print(f"  - Allowed entities: {ieeg.allowed_entities}")
            print(f"  - Required entities: {ieeg.required_entities}")
            print(f"  - Suffixes: {ieeg.suffixes}")
            print(f"  - Extensions: {ieeg.extensions}")
            
            # Test metadata requirements (dynamically extracted)
            requirements = ieeg.metadata_requirements
            print(f"  - Required metadata ({len(requirements.get('required', {}))}): {list(requirements.get('required', {}).keys())}")
            print(f"  - Recommended metadata ({len(requirements.get('recommended', {}))}): {list(requirements.get('recommended', {}).keys())}")
        
        # Test file registry
        if manager.file_registry:
            print(f"\nFile extensions for iEEG: {manager.file_registry.get_supported_extensions('ieeg')}")
        
        # Test entity validation
        print(f"\nEntity validation tests:")
        print(f"  - sub '01': {manager.validate_entity_value('sub', '01')}")
        print(f"  - sub 'invalid-': {manager.validate_entity_value('sub', 'invalid-')}")
        print(f"  - run '1': {manager.validate_entity_value('run', '1')}")
        print(f"  - run 'abc': {manager.validate_entity_value('run', 'abc')}")
        
        # Test that we're parsing everything dynamically
        print(f"\nDynamic parsing verification:")
        print(f"  - Schema version: {manager.get_schema_version()}")
        schema_info = manager.get_schema_info()
        print(f"  - Total entities: {schema_info.get('num_entities')}")
        print(f"  - Total datatypes: {schema_info.get('num_datatypes')}")
        print(f"  - Total metadata fields: {schema_info.get('num_metadata_fields')}")
        print(f"  - Total suffixes: {schema_info.get('num_suffixes')}")
        print(f"  - Total extensions: {schema_info.get('num_extensions')}")
        
        print("\n✅ Schema loading test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Schema loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_schema_loading()
    sys.exit(0 if success else 1)