#!/usr/bin/env python
"""
Test the converter system with a real TRC file
"""

from pathlib import Path
import tempfile
import json
from bidsificator.converters.registry import ConverterRegistry

def test_converters():
    # Initialize registry
    print("=" * 60)
    print("CONVERTER SYSTEM TEST")
    print("=" * 60)
    
    registry = ConverterRegistry()
    
    # Test file path - must be provided as argument or environment variable
    import os
    import sys
    
    trc_file_path = None
    if len(sys.argv) > 1:
        trc_file_path = sys.argv[1]
    elif os.getenv('TRC_TEST_FILE'):
        trc_file_path = os.getenv('TRC_TEST_FILE')
    else:
        print("❌ No test file provided.")
        print("Usage: python test_converters.py <path_to_trc_file>")
        print("   or: TRC_TEST_FILE=<path> python test_converters.py")
        return
        
    trc_file = Path(trc_file_path)
    
    if not trc_file.exists():
        print(f"❌ Test file not found: {trc_file}")
        return
    
    print(f"✓ Test file found: {trc_file}")
    print(f"  File size: {trc_file.stat().st_size / 1024:.1f} KB")
    print()
    
    # Test 1: Check all available converters
    print("1. AVAILABLE CONVERTERS FOR TRC FILE:")
    print("-" * 40)
    
    converters = registry.get_all_converters(trc_file)
    if not converters:
        print("❌ No converters found for TRC file")
        return
    
    for i, converter in enumerate(converters, 1):
        print(f"  {i}. {converter.description}")
        print(f"     Priority: {converter.priority}")
        print(f"     Target: {converter.target_format}")
    print()
    
    # Test 2: Check default converter selection
    print("2. DEFAULT CONVERTER SELECTION:")
    print("-" * 40)
    
    default_converter = registry.get_converter(trc_file)
    if not default_converter:
        print("❌ No default converter selected")
        return
    
    print(f"✓ Default converter: {default_converter.description}")
    print(f"  Priority: {default_converter.priority}")
    print()
    
    # Test 3: Test EDF conversion
    print("3. TESTING TRC → EDF CONVERSION:")
    print("-" * 40)
    
    edf_converter = registry.get_converter(trc_file, target_format='.edf')
    if not edf_converter:
        print("❌ EDF converter not found")
    else:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = edf_converter.convert(trc_file, Path(tmpdir))
                print(f"✓ Conversion successful!")
                print(f"  Output: {output_path.name}")
                print(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")
                
                # Extract metadata
                metadata = edf_converter.extract_metadata(trc_file)
                print(f"✓ Metadata extracted ({len(metadata)} fields):")
                for key, value in list(metadata.items())[:10]:  # Show first 10
                    if isinstance(value, dict):
                        print(f"    {key}: <dict with {len(value)} items>")
                    elif isinstance(value, list):
                        print(f"    {key}: {value[:3]}..." if len(value) > 3 else f"    {key}: {value}")
                    else:
                        print(f"    {key}: {value}")
                if len(metadata) > 10:
                    print(f"    ... and {len(metadata) - 10} more fields")
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
    print()
    
    # Test 4: Test BrainVision conversion
    print("4. TESTING TRC → BRAINVISION CONVERSION:")
    print("-" * 40)
    
    bv_converter = registry.get_converter(trc_file, target_format='.vhdr')
    if not bv_converter:
        print("❌ BrainVision converter not found")
    else:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = bv_converter.convert(trc_file, Path(tmpdir))
                print(f"✓ Conversion successful!")
                print(f"  Output: {output_path.name}")
                
                # Check all BrainVision files created
                tmpdir_path = Path(tmpdir)
                vhdr_files = list(tmpdir_path.glob('*.vhdr'))
                vmrk_files = list(tmpdir_path.glob('*.vmrk'))
                eeg_files = list(tmpdir_path.glob('*.eeg'))
                
                print(f"  Created files:")
                if vhdr_files:
                    print(f"    - {vhdr_files[0].name} (header)")
                if vmrk_files:
                    print(f"    - {vmrk_files[0].name} (markers)")
                if eeg_files:
                    print(f"    - {eeg_files[0].name} (data, {eeg_files[0].stat().st_size / 1024:.1f} KB)")
                    
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
    print()
    
    # Test 5: Test converter registry methods
    print("5. REGISTRY METHODS TEST:")
    print("-" * 40)
    
    # Test needs_conversion
    needs_conv = registry.needs_conversion(trc_file)
    print(f"  needs_conversion(): {needs_conv} {'✓' if needs_conv else '❌'}")
    
    # Test target formats
    target_formats = registry.get_available_target_formats(trc_file)
    print(f"  Available targets: {target_formats}")
    
    # Test converter by name
    conv_by_name = registry.get_converter_by_name("TrcToEdfConverter")
    print(f"  Get by name: {'✓' if conv_by_name else '❌'} TrcToEdfConverter")
    
    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_converters()