#!/usr/bin/env python
"""
Debug TRC file detection
"""

from pathlib import Path
import warnings
import mne
import neo

def debug_trc_file(trc_path=None):
    if trc_path is None:
        import sys
        import os
        if len(sys.argv) > 1:
            trc_path = sys.argv[1]
        elif os.getenv('TRC_TEST_FILE'):
            trc_path = os.getenv('TRC_TEST_FILE')
        else:
            print("❌ No TRC file provided.")
            print("Usage: python debug_trc.py <path_to_trc_file>")
            print("   or: TRC_TEST_FILE=<path> python debug_trc.py")
            return
    
    trc_file = Path(trc_path)
    
    print(f"File exists: {trc_file.exists()}")
    print(f"File suffix: '{trc_file.suffix}'")
    print(f"Suffix lower: '{trc_file.suffix.lower()}'")
    print(f"Size: {trc_file.stat().st_size / (1024*1024):.1f} MB")
    
    # Test NEO reading
    print("\nTrying to read with NEO MicromedIO...")
    try:
        reader = neo.io.MicromedIO(filename=str(trc_file))
        block = reader.read_block(lazy=True)
        
        print(f"✓ NEO can read the file")
        print(f"  Segments: {len(block.segments)}")
        
        if block.segments:
            segment = block.segments[0]
            print(f"  Analog signals in first segment: {len(segment.analogsignals)}")
            
            if segment.analogsignals:
                first_signal = segment.analogsignals[0]
                print(f"  First signal shape: {first_signal.shape}")
                print(f"  Sampling rate: {first_signal.sampling_rate}")
                print(f"  Duration: {first_signal.duration}")
                print(f"  Name: {getattr(first_signal, 'name', 'Unknown')}")
        
        # Try to get block metadata
        if hasattr(block, 'rec_datetime'):
            print(f"  Recording time: {block.rec_datetime}")
        
    except Exception as e:
        print(f"❌ NEO failed to read: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_trc_file()