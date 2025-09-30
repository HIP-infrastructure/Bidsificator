# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bidsificator is a PyQt6 application for managing BIDS (Brain Imaging Data Structure) files through a GUI. It helps organize neuroimaging data into the BIDS format with features for importing subjects, validating datasets, and editing metadata.

## Development Setup

```bash
# Setup environment with Poetry
poetry env use $(pyenv which python3.11)  # Python 3.10-3.12 supported
poetry install

# Run the GUI application
poetry run bidsificator

# Run the API server (debug mode)
poetry run bidsificator-api

# Open Qt Designer
poetry run make design

# Rebuild UI from .ui files
poetry run make build-ui
```

## Architecture

### MVC Pattern
The application follows Model-View-Controller architecture:

- **Controllers** (`bidsificator/controllers/`): Business logic coordination
  - `MainController`: Orchestrates all sub-controllers
  - `DatasetController`: Dataset operations
  - `ImportFilesController`: Single file imports
  - `ImportSubjectsController`: Batch subject imports
  - `FileEditorController`: Metadata editing
  - `PatientTableController`: Patient table operations
  - `OptionController`: Configuration management

- **Models** (`bidsificator/models/`): Data management
  - `DatasetModel`: Dataset state
  - `ImportFileModel`: Import file state
  - `ImportSessionModel`: Import session state
  - `SubjectDataModel`: Subject data

- **Views** (`bidsificator/ui/`): PyQt6 UI components
  - `MainWindow`: Main application window
  - `FileEditor`: File metadata editor
  - `PatientTableWidget`: Subject display
  - `OptionWindow`: Settings dialog

- **Services** (`bidsificator/services/`): Reusable business logic
  - `DataCrawlerService`: File system crawling
  - `FileDetectionService`: File type detection
  - `ImportService`: Import operations
  - `ValidationService`: BIDS validation

### Core Components

- **BIDS Classes** (`bidsificator/core/`):
  - `BidsFolder`: BIDS dataset management
  - `BidsSubject`: Subject-level operations
  - `DataCrawler`: File discovery
  - `validators`: BIDS compliance validation

- **Workers** (`bidsificator/workers/`): Background processing
  - `BidsSubjectsProcess`: Subject processing
  - `BidsFilesProcss`: File processing
  - `ImportBidsFilesWorker`: File import worker
  - `ImportBidsSubjectsWorker`: Subject import worker

### UI Forms
- Generated from `.ui` files in `bidsificator/forms/`
- Use `poetry run make build-ui` to regenerate after changes

### Configuration
- Config files in `bidsificator/config/`:
  - `config.yaml`: Active configuration
  - `config.example.yaml`: Template
  - Site-specific configs (e.g., `config.lyon.yaml`)

## Key Features

1. **Dataset Management**: Create/open BIDS datasets, manage subjects and sessions
2. **Import Operations**: Single file or batch subject imports with metadata
3. **Validation**: BIDS compliance checking for datasets and subjects
4. **File Detection**: Automatic detection of neuroimaging file types (EEG, MRI)
5. **API Server**: Flask-based REST API for programmatic access

## Dependencies

- PyQt6 for GUI
- NumPy for data processing
- dicom2nifti for DICOM conversion
- bids_validator for compliance checking
- Flask ecosystem for API server

## BIDS Schema-Driven Architecture

### Core Architecture Principles
- **Always use schema-driven approaches** - Never hardcode BIDS metadata fields, entities, or validation rules. Extract everything from the BIDS schema at `bidsificator/schema/bids_schema.json`
- **BidsSchemaManager is singleton** - Use `BidsSchemaManager.get_instance()` to access schema data. It loads 14 datatypes and ~30 recommended iEEG fields when working correctly
- **Schema parser location** - Critical schema parsing logic is in `bidsificator/core/schema/parser.py`, especially the `_extract_metadata_requirements()` method
- **Current schema version** - BIDS 1.10.0, schema version 0.11.3

### BIDS Validation Philosophy
- **Fix root causes, never skip validation** - When encountering BIDS validation errors, implement proper schema-compliant solutions rather than workarounds or skipping checks
- **Field omission per BIDS spec** - BIDS specification states: "It is RECOMMENDED that non-compulsory metadata fields are fully omitted when they are unavailable or unapplicable, instead of specified with an 'n/a' value"
- **Warnings vs Errors** - BIDS validator warnings about missing RECOMMENDED fields are expected and correct when values are unavailable. Do not add placeholder values just to silence warnings.
- **Standard BIDS columns protection** - Never redefine standard columns (`onset`, `duration`, `trial_type`, `response_time`) in events.json to avoid `TSV_COLUMN_TYPE_REDEFINED` warnings
- **User responsibility fields** - Leave user-specific fields (like `Authors`) empty rather than adding placeholder text

### Key Implementation Patterns
- **Metadata extraction workflow**: Schema → Parser → Datatype requirements → BidsSubjectSchema generation
- **Entity ordering**: Use `get_entity_order()` from `bids_constants.py` - extracts canonical order from schema (31 entities in BIDS 1.10.1)
- **Suffix selection**: Use `get_default_suffix_for_datatype()` - schema-driven with smart defaults (prioritizes datatype name, filters metadata suffixes, prefers T1w for anat)
- **Filename/path building**: Use `FilenameBuilder` class - centralizes all filename construction with schema validation, supports parsing, and entity suggestions
  - `build_filename()` - Create BIDS-compliant filename from entities
  - `build_path()` - Create complete BIDS path including directory structure
  - `parse_filename()` - Extract entities from existing BIDS filename
  - `suggest_entities_for_datatype()` - Get commonly used entities for datatype
- **Events.json generation**: Check for HED columns → Add HEDVersion if needed → Define only non-standard columns
- **HED support**: When HED columns detected, add `HEDVersion` field (schema defines format but no default - use compatible version like "8.2.0")
- **Schema compatibility**: HED 8.2.0 works with BIDS 1.10.0

### File Locations & Responsibilities
- `bidsificator/core/BidsSubjectSchema.py` - Main metadata generation logic, contains `_get_default_metadata_value()` method
- `bidsificator/core/BidsFolder.py` - Dataset-level file generation (README, dataset_description.json)
- `bidsificator/core/filename_builder.py` - **Schema-driven filename/path builder** with validation, parsing, and entity suggestions
- `bidsificator/core/schema/` - All schema parsing and management
  - `parser.py` - Contains critical `_extract_metadata_requirements()` method
  - `models.py` - BidsEntity and BidsDatatype definitions
  - `manager.py` - BidsSchemaManager singleton
- **Schema-driven metadata flow**: `BidsSchemaManager` → `BidsDatatype.get_*_metadata()` → `BidsSubjectSchema._get_default_metadata_value()`
- **Schema-driven filename flow**: `FilenameBuilder` → validates entities → applies canonical ordering → builds BIDS-compliant paths

### Common Pitfalls to Avoid
- **Missing parser cases** - Always check if new requirement levels (like string "recommended") are handled in `parser.py:_extract_metadata_requirements()`
- **Duplicate field addition** - Check for `None` values before adding metadata fields to prevent validation errors
- **Hardcoded values** - Never hardcode entities, suffixes, or BIDS version. Use schema extraction: `get_entity_order()`, `get_default_suffix_for_datatype()`, `schema_manager.get_bids_version()`
- **Schema loading issues** - If `len(manager.datatypes)` returns 0 instead of 15, check parser logic

### Debugging Schema Issues
- **Check datatype count** - `len(manager.datatypes)` should be 15, not 0
- **Check entity count** - `len(get_entity_order())` should be 31 for BIDS 1.10.1
- **Verify metadata extraction** - `ieeg.get_recommended_metadata()` should return ~30 fields for iEEG, `anat.get_recommended_metadata()` should return ~56 fields for anatomical MRI
- **Test suffix selection** - `get_default_suffix_for_datatype('ieeg')` should return 'ieeg', `get_default_suffix_for_datatype('anat')` should return 'T1w'
- **Test metadata generation** - Use `BidsSubject._get_default_metadata_value()` to verify field handling
- **Parser debugging** - Check `parser.py` for missing field_rule cases like `field_rule == "recommended"`
- **Modality-to-datatype mapping** - Critical fix: `_extract_modality_mappings()` must return `Dict[str, List[str]]` to handle modalities that apply to multiple datatypes (e.g., "mri" rules apply to anat, func, dwi, fmap, perf)

### BIDS Validation Warnings & Errors
- **SIDECAR_KEY_RECOMMENDED** (WARNING) - This warning is **expected and correct** when source data lacks recommended metadata. Per BIDS spec, omit unavailable fields rather than using placeholders. Our ValidationService replicates this warning. **Strategy**: Use HYBRID approach - conservative defaults for some fields (ParallelReductionFactors → 1, NonlinearGradientCorrection → false), omit sequence-specific fields (MagneticFieldStrength, EchoTime, FlipAngle, DwellTime).
- **TOO_FEW_AUTHORS** (WARNING) - Expected when Authors field is empty or has one entry. Our ValidationService checks for this.
- **SLICETIMING_ELEMENTS** (WARNING) - SliceTiming array must match NIfTI k-dimension. Our ValidationService validates this.
- **JSON_SCHEMA_VALIDATION_ERROR** (ERROR) - Data type mismatch. Return `None` to omit fields when data type cannot be satisfied. **Critical**: Filter `None` values before JSON serialization. Never set numeric/boolean/array fields to string values like `"n/a"`.
- **EFFECTIVEECHOSPACING_LARGER_THAN_TOTALREADOUTTIME** (ERROR) - Field relationship validation error. Omit both fields when relationship cannot be ensured.
- **HED_ERROR** (ERROR) - Usually caused by `None` values in JSON fields that validator tries to process. Ensure proper field omission and HEDVersion when HED columns present.
- **TSV_ADDITIONAL_COLUMNS_UNDEFINED** (ERROR) - Generate events.json with column definitions
- **TSV_COLUMN_TYPE_REDEFINED** (WARNING) - Skip standard BIDS columns in events.json generation
- **README_FILE_MISSING** (WARNING) - Generate README automatically in `create_folders()`

### Known Working Metadata Field Counts (After All Fixes)
- **iEEG datatype**: ~30 recommended fields (electrophysiology-specific)
- **anat datatype**: ~56 recommended fields (MRI equipment + acquisition parameters)
- **func datatype**: ~56 recommended fields (inherits MRI fields + functional-specific)
- **dwi datatype**: ~56 recommended fields (inherits MRI fields + diffusion-specific)
- **Total schema datatypes**: 14 (when parser working correctly)

### MRI Metadata Field Categories (for anat/func/dwi/fmap/perf)
Per BIDS spec: "non-compulsory metadata fields are fully omitted when unavailable, instead of specified with 'n/a'"

- **Equipment (strings)**: Manufacturer, ManufacturersModelName, DeviceSerialNumber, StationName → `"n/a"` (identifiers, not measurements)
- **Sequence (strings)**: SoftwareVersions, PulseSequenceType, ScanningSequence, SequenceVariant → `"n/a"` (descriptive text)
- **Coil (strings)**: ReceiveCoilName, ReceiveCoilActiveElements, MatrixCoilMode, CoilCombinationMethod → `"n/a"`
- **Institution (strings)**: InstitutionName, InstitutionAddress, InstitutionalDepartmentName → `"n/a"`
- **Conservative defaults (numeric)**: ParallelReductionFactorInPlane, ParallelReductionFactorOutOfPlane → `1` (no acceleration when unknown)
- **Conservative defaults (boolean)**: NonlinearGradientCorrection → `false` (no correction when unknown)
- **Acquisition (numeric - OMIT)**: MagneticFieldStrength, EchoTime, FlipAngle, DwellTime → **OMIT** (`None`) - sequence-specific measurements, no reasonable defaults. BIDS validator will warn (expected).
- **Advanced (numeric - OMIT)**: EffectiveEchoSpacing, TotalReadoutTime, InversionTime, MixingTime → **OMIT** (`None`)
- **Boolean fields (OMIT)**: MTState, SpoilingState → **OMIT** (`None`) - avoid false assumptions
- **Array fields (OMIT)**: TablePosition → **OMIT** (`None`)
- **Enum fields (OMIT)**: MTPulseShape, SpoilingType → **OMIT** (`None`)
- **Special strings**: MRAcquisitionType → `"3D"` (for anat), PulseSequenceDetails → `"Information not available..."`

### Critical Data Type Rules
- **String fields** can use `"n/a"` as default value
- **Numeric, boolean, array, enum fields** MUST return `None` (omit) when unknown to prevent `JSON_SCHEMA_VALIDATION_ERROR`
- **Never set numeric fields to string values** like `"n/a"` - causes schema validation failures
- **JSON serialization**: Always filter out `None` values before writing JSON (`{k: v for k, v in metadata.items() if v is not None}`)
- **Relationship validation**: Some fields have interdependencies (e.g., EffectiveEchoSpacing < TotalReadoutTime)