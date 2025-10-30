# Schema-Driven BidsSubject Implementation

## Overview

The new `BidsSubjectSchema` class replaces the hardcoded `BidsSubject` with a dynamic, schema-driven implementation that adapts to the official BIDS specification.

## Key Improvements

### ✅ **Removed Issues from Original**
- ❌ **No more inline classes** - Proper `FileAnalysis` abstraction
- ❌ **No hardcoded entity order** - Uses `ENTITY_ORDER` from constants
- ❌ **No hardcoded suffixes** - Uses `DEFAULT_SUFFIXES` configuration
- ❌ **No magic strings** - Centralized constants in `bids_constants.py`
- ❌ **No hardcoded file extensions** - Uses `BIDS_DATA_EXTENSIONS`
- ❌ **No hardcoded channel counts** - Configurable via `DEFAULT_CHANNEL_COUNTS`

### ✅ **New Features**
- 🎯 **Schema-driven validation** - All validation uses BIDS schema
- 🔄 **Conversion integration** - Built-in support for TRC→EDF/BrainVision
- 🏗️ **Modular architecture** - Clean separation of concerns
- 🎛️ **Configurable defaults** - Easy to customize behavior
- 📊 **Better error handling** - Clear validation messages
- 🔍 **File analysis system** - Proper abstraction for file processing

## Architecture

### Core Components

```python
# Main class
from bidsificator.core.BidsSubjectSchema import BidsSubject

# Supporting modules
from bidsificator.core.file_analysis import FileAnalysis
from bidsificator.core.bids_constants import (
    DEFAULT_SUFFIXES,
    DEFAULT_METADATA_VALUES,
    ENTITY_ORDER
)
```

### Dependencies
- `BidsSchemaManager` - Dynamic BIDS schema parsing
- `ConverterRegistry` - File format conversion system
- `pandas` - TSV file generation
- Standard library: `json`, `shutil`, `pathlib`, `tempfile`

## Usage Examples

### Basic Usage

```python
from pathlib import Path
from bidsificator.core.schema import BidsSchemaManager
from bidsificator.core.BidsSubjectSchema import BidsSubject

# Initialize schema and subject
schema = BidsSchemaManager()
schema.load_schema()

dataset_path = Path("/path/to/bids/dataset")
subject = BidsSubject("01", dataset_path, schema)

# Add optional metadata for all files
subject.set_optional_metadata({
    'Institution': 'My University',
    'PowerLineFrequency': 50
})
```

### Adding Files with Conversion

```python
# Add TRC file - will auto-convert to EDF
source_trc = Path("/data/subject01/recording.TRC")

result = subject.add_file(
    source_path=source_trc,
    datatype='ieeg',
    entities={
        'ses': 'pre',
        'task': 'rest',
        'run': '1'
    },
    metadata={
        'TaskDescription': 'Resting state recording'
    }
)

print(f"Success: {result['success']}")
print(f"Target: {result['target_path']}")
print(f"Converted: {result['converted']}")
# Output: sub-01/ses-pre/ieeg/sub-01_ses-pre_task-rest_run-1_ieeg.edf
```

### File Analysis

```python
# Analyze file before processing
analysis = subject.analyze_file(source_trc)

if analysis.is_valid:
    print(f"File type: {analysis.bids_datatype}")
    print(f"Needs conversion: {analysis.needs_conversion}")
    print(f"Converter: {analysis.converter_name}")
else:
    print(f"Error: {analysis.error}")
```

### Working with Sessions and Datatypes

```python
# Create datatype paths
ieeg_path = subject.get_datatype_path('ieeg', 'pre')  # ses-pre/ieeg/
anat_path = subject.get_datatype_path('anat')         # anat/

# List existing data
sessions = subject.get_sessions()          # ['pre', 'post']
datatypes = subject.get_datatypes('pre')   # ['ieeg', 'anat']
files = subject.list_files('ieeg', 'pre')  # [Path to iEEG files]
```

## Configuration

### Customizable Constants

All hardcoded values are now configurable via `bids_constants.py`:

```python
# Default suffixes by datatype
DEFAULT_SUFFIXES = {
    'ieeg': 'ieeg',
    'eeg': 'eeg',
    'anat': 'T1w',
    'func': 'bold'
}

# Entity ordering for filenames
ENTITY_ORDER = [
    'sub', 'ses', 'task', 'acq', 'ce', 'rec', 
    'dir', 'run', 'echo', 'recording', 'space'
]

# Channel counts by modality
DEFAULT_CHANNEL_COUNTS = {
    'ieeg': 64,
    'eeg': 64,
    'meg': 306,
    'nirs': 32
}
```

### Metadata Defaults

```python
DEFAULT_METADATA_VALUES = {
    'UNKNOWN': 'unknown',
    'NOT_AVAILABLE': 'n/a',
    'GOOD_STATUS': 'good',
    'BAD_STATUS': 'bad'
}
```

## Generated Files

### Automatic Metadata Generation

For each data file, the system automatically generates:

#### JSON Sidecar
```json
{
  "InstitutionName": "My University",
  "PowerLineFrequency": 50,
  "SamplingFrequency": 1024,
  "TaskName": "rest",
  "iEEGReference": "average"
}
```

#### Channels TSV (for EEG/iEEG/MEG)
```tsv
name    type    units   sampling_frequency  status
CH001   SEEG    µV      n/a                 good
CH002   SEEG    µV      n/a                 good
...
```

#### Events TSV (for EEG/iEEG/MEG)
```tsv
onset   duration    trial_type  response_time   value
```

## API Reference

### Main Methods

#### `__init__(subject_id, dataset_path, schema_manager)`
Initialize subject with schema validation.

#### `add_file(source_path, datatype, entities=None, suffix=None, metadata=None, target_format=None)`
Add file with automatic conversion and BIDS naming.

**Returns:** Dict with success status, target path, and conversion info.

#### `analyze_file(source_path, target_format=None)`
Analyze file for BIDS processing without actually processing it.

**Returns:** `FileAnalysis` object with processing information.

#### `get_datatype_path(datatype, session=None)`
Get/create path for specific datatype and optional session.

#### `set_optional_metadata(metadata)`
Set metadata that will be included in all files for this subject.

### Utility Methods

#### `rename_subject(new_subject_id)`
Rename subject and update all associated files.

#### `list_files(datatype=None, session=None)`
List data files for subject, optionally filtered by datatype/session.

#### `get_sessions()` / `get_datatypes(session=None)`
Get lists of existing sessions and datatypes.

## Testing

Run comprehensive tests:

```bash
poetry run python tests/test_bids_subject_improved.py
```

Tests cover:
- ✅ Subject creation and validation
- ✅ File analysis system
- ✅ Constants system
- ✅ Path building with entity ordering
- ✅ Datatype path creation
- ✅ Optional metadata handling
- ✅ Helper method functionality
- ✅ Metadata file generation
- ✅ Session and datatype listing
- ✅ File listing capabilities

## Migration from Old BidsSubject

### Key Changes
1. **Constructor**: Now requires `BidsSchemaManager`
2. **No hardcoded sessions**: Use any session names
3. **Entity validation**: All entities validated against schema
4. **Conversion integration**: Built-in format conversion
5. **Better error messages**: Schema-driven validation errors

### Migration Example

```python
# Old way
old_subject = BidsSubject("/dataset", "sub-01")
old_subject.add_functionnal_file(file_path, entities)

# New way  
schema = BidsSchemaManager()
schema.load_schema()
new_subject = BidsSubject("01", Path("/dataset"), schema)
new_subject.add_file(file_path, 'ieeg', entities)
```

## Future Enhancements

- [ ] **Config file support**: Load constants from YAML/JSON
- [ ] **Plugin system**: Custom converters and validators
- [ ] **Batch operations**: Process multiple files at once
- [ ] **Template system**: Custom metadata templates per site
- [ ] **Validation hooks**: Custom validation rules
- [ ] **Progress callbacks**: UI integration support

---

*This implementation provides a solid foundation for BIDS-compliant data organization with full schema validation and automatic format conversion.*