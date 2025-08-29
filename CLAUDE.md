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