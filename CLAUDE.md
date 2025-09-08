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
- **Field omission vs default values** - Some BIDS fields should be omitted (return `None`) rather than given default values (e.g., `EpochLength` for continuous recordings)
- **Standard BIDS columns protection** - Never redefine standard columns (`onset`, `duration`, `trial_type`, `response_time`) in events.json to avoid `TSV_COLUMN_TYPE_REDEFINED` warnings
- **User responsibility fields** - Leave user-specific fields (like `Authors`) empty rather than adding placeholder text

### Key Implementation Patterns
- **Metadata extraction workflow**: Schema → Parser → Datatype requirements → BidsSubjectSchema generation
- **Events.json generation**: Check for HED columns → Add HEDVersion if needed → Define only non-standard columns
- **HED support**: When HED columns detected, add `HEDVersion` field (schema defines format but no default - use compatible version like "8.2.0")
- **Schema compatibility**: HED 8.2.0 works with BIDS 1.10.0

### File Locations & Responsibilities
- `bidsificator/core/BidsSubjectSchema.py` - Main metadata generation logic, contains `_get_default_metadata_value()` method
- `bidsificator/core/BidsFolder.py` - Dataset-level file generation (README, dataset_description.json)  
- `bidsificator/core/schema/` - All schema parsing and management
  - `parser.py` - Contains critical `_extract_metadata_requirements()` method
  - `models.py` - BidsEntity and BidsDatatype definitions
  - `manager.py` - BidsSchemaManager singleton
- **Schema-driven metadata flow**: `BidsSchemaManager` → `BidsDatatype.get_*_metadata()` → `BidsSubjectSchema._get_default_metadata_value()`

### Common Pitfalls to Avoid
- **Missing parser cases** - Always check if new requirement levels (like string "recommended") are handled in `parser.py:_extract_metadata_requirements()`
- **Duplicate field addition** - Check for `None` values before adding metadata fields to prevent validation errors
- **Hardcoded field lists** - Use schema extraction instead of manually listing metadata fields
- **Schema loading issues** - If `len(manager.datatypes)` returns 0 instead of 14, check parser logic

### Debugging Schema Issues
- **Check datatype count** - `len(manager.datatypes)` should be 14, not 0
- **Verify metadata extraction** - `ieeg.get_recommended_metadata()` should return ~30 fields for iEEG
- **Test metadata generation** - Use `BidsSubjectSchema._get_default_metadata_value()` to verify field handling
- **Parser debugging** - Check `parser.py` for missing field_rule cases like `field_rule == "recommended"`

### BIDS Validation Error Patterns
- **SIDECAR_KEY_RECOMMENDED** - Add recommended fields via schema-driven metadata extraction
- **TSV_ADDITIONAL_COLUMNS_UNDEFINED** - Generate events.json with column definitions
- **TSV_COLUMN_TYPE_REDEFINED** - Skip standard BIDS columns in events.json generation
- **JSON_SCHEMA_VALIDATION_ERROR** - Return `None` for fields that should be omitted
- **HED_ERROR** - Add `HEDVersion` field when HED columns are present, never skip HED validation
- **README_FILE_MISSING** - Generate README automatically in `create_folders()`