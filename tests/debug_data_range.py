#!/usr/bin/env python
"""
Debug data range in TRC file
"""

from pathlib import Path
import neo
import numpy as np

def debug_data_range(trc_path=None):
    if trc_path is None:
        import sys
        import os
        if len(sys.argv) > 1:
            trc_path = sys.argv[1]
        elif os.getenv('TRC_TEST_FILE'):
            trc_path = os.getenv('TRC_TEST_FILE')
        else:
            print("❌ No TRC file provided.")
            print("Usage: python debug_data_range.py <path_to_trc_file>")
            print("   or: TRC_TEST_FILE=<path> python debug_data_range.py")
            return
    
    trc_file = Path(trc_path)
    
    # Read TRC file with neo
    reader = neo.io.MicromedIO(filename=str(trc_file))
    block = reader.read_block(lazy=True)
    
    segment = block.segments[0]
    analog_signals = segment.analogsignals
    
    print(f"Number of analog signals: {len(analog_signals)}")
    
    for i, sig in enumerate(analog_signals):
        print(f"\nSignal {i}:")
        print(f"  Shape: {sig.shape}")
        print(f"  Data type: {sig.dtype}")
        print(f"  Units: {sig.units}")
        print(f"  Sampling rate: {sig.sampling_rate}")
        
        # Load a small sample to check range
        if hasattr(sig, 'load') and callable(sig.load):
            sample = sig.load(time_slice=(0, min(1000, sig.shape[0])))  # First 1000 samples
        else:
            sample = sig[:1000]  # First 1000 samples
            
        print(f"  Min value: {np.min(sample.magnitude)}")
        print(f"  Max value: {np.max(sample.magnitude)}")
        print(f"  Mean: {np.mean(sample.magnitude)}")
        print(f"  Std: {np.std(sample.magnitude)}")

if __name__ == "__main__":
    debug_data_range()