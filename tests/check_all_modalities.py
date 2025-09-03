#!/usr/bin/env python
"""
Check all available modalities and their details in BIDS schema
"""

from bidsificator.core.schema import BidsSchemaManager

def main():
    # Load schema
    manager = BidsSchemaManager()
    manager.load_schema()
    
    print("=" * 80)
    print("BIDS SCHEMA MODALITIES SUMMARY")
    print("=" * 80)
    print(f"BIDS Version: {manager.get_bids_version()}")
    print(f"Schema Version: {manager.get_schema_version()}")
    
    # Group datatypes by category
    neurophysiology = ['ieeg', 'eeg', 'meg', 'nirs']
    imaging = ['anat', 'func', 'dwi', 'fmap', 'perf', 'pet', 'micr']
    behavioral = ['beh', 'motion']
    spectroscopy = ['mrs']
    
    categories = [
        ("🧠 NEUROPHYSIOLOGY", neurophysiology),
        ("🎯 IMAGING", imaging), 
        ("🎭 BEHAVIORAL", behavioral),
        ("🧪 SPECTROSCOPY", spectroscopy)
    ]
    
    for category_name, datatypes in categories:
        print(f"\n{category_name}")
        print("-" * 60)
        
        for datatype in datatypes:
            if datatype in manager.datatypes:
                dt = manager.get_datatype(datatype)
                print(f"\n📁 {datatype.upper()} Datatype:")
                print(f"   Entities: {len(dt.allowed_entities)} allowed ({dt.required_entities} required)")
                print(f"   Suffixes: {len(dt.suffixes)} - {dt.suffixes[:5]}{'...' if len(dt.suffixes) > 5 else ''}")
                
                # Get extensions for this datatype
                extensions = manager.file_registry.get_supported_extensions(datatype)
                print(f"   Extensions: {extensions}")
                
                # Get metadata requirements
                metadata_reqs = dt.metadata_requirements
                required_count = len(metadata_reqs.get('required', {}))
                recommended_count = len(metadata_reqs.get('recommended', {}))
                print(f"   Metadata: {required_count} required, {recommended_count} recommended")
                
                # Show some key required metadata
                required_meta = list(metadata_reqs.get('required', {}).keys())[:3]
                if required_meta:
                    print(f"   Key fields: {', '.join(required_meta)}")
    
    # Show detailed info for neurophysiology datatypes
    print(f"\n{'='*80}")
    print("DETAILED NEUROPHYSIOLOGY INFORMATION")
    print(f"{'='*80}")
    
    for datatype in neurophysiology:
        if datatype in manager.datatypes:
            dt = manager.get_datatype(datatype)
            
            print(f"\n🔬 {datatype.upper()} DETAILED INFO:")
            print(f"   Full entity list: {dt.allowed_entities}")
            print(f"   Required entities: {dt.required_entities}")
            print(f"   All suffixes: {dt.suffixes}")
            
            metadata_reqs = dt.metadata_requirements
            required_meta = metadata_reqs.get('required', {})
            recommended_meta = metadata_reqs.get('recommended', {})
            
            if required_meta:
                print(f"   Required metadata ({len(required_meta)}):")
                for field, spec in list(required_meta.items())[:8]:  # Show first 8
                    field_type = spec.get('type', 'unknown')
                    print(f"     • {field} ({field_type})")
                if len(required_meta) > 8:
                    print(f"     ... and {len(required_meta) - 8} more")
            
            if recommended_meta:
                print(f"   Recommended metadata ({len(recommended_meta)}):")
                for field in list(recommended_meta.keys())[:5]:  # Show first 5
                    print(f"     • {field}")
                if len(recommended_meta) > 5:
                    print(f"     ... and {len(recommended_meta) - 5} more")

if __name__ == "__main__":
    main()