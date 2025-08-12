# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bidsificator is a PyQt6 application for managing BIDS (Brain Imaging Data Structure) files through a graphical user interface. The project also includes a Flask API for programmatic access to BIDS dataset operations.

## Development Commands

### Environment Setup
```bash
# Use poetry (installed via pipx) for dependency management
# Set up Python environment (3.10, 3.11, or 3.12 supported)
poetry env use $(pyenv which python3.10)  # or python3.11, python3.12
poetry install
```

### Running the Application
```bash
# Run the PyQt6 GUI application
poetry run bidsificator

# Run the Flask API server (debug mode)
poetry run bidsificator-api
```

### UI Development
```bash
# Open Qt Designer to edit UI forms
poetry run make design

# Rebuild Python UI files from Qt Designer .ui files
poetry run make build-ui
```

## Architecture

### Core Components

1. **PyQt6 GUI Application** (`bidsificator/ui/`)
   - `MainWindow.py`: Main application window, coordinates all UI operations
   - `FileEditor.py`: Editor for BIDS files
   - `OptionWindow.py`: Configuration options interface
   - `PatientTableWidget.py`: Widget for displaying patient/subject data
   - UI forms are designed in Qt Designer (`forms/*.ui`) and compiled to Python (`forms/*_ui.py`)

2. **Core BIDS Logic** (`bidsificator/core/`)
   - `BidsFolder.py`: Manages BIDS dataset folder structure and operations
   - `BidsSubject.py`: Handles individual BIDS subject data and file operations
   - `BidsUtilityFunctions.py`: Utility functions for BIDS operations
   - `DataCrawler.py`: Crawls directories to find and organize BIDS data based on configuration patterns
   - `OptionFile.py`: Manages option/configuration files
   - `PyEEGFormat/`: Platform-specific EEG format wrappers (auto-selected based on OS/architecture)

3. **Background Workers** (`bidsificator/workers/`)
   - `ImportBidsFilesWorker.py`: Asynchronous file import operations
   - `ImportBidsSubjectsWorker.py`: Asynchronous subject import operations
   - `BidsFilesProcss.py`: BIDS file processing logic
   - `BidsSubjectsProcess.py`: BIDS subject processing logic

4. **Flask API** (`bidsificator/api.py`)
   - RESTful API for BIDS operations
   - Swagger UI documentation at `/apidocs`
   - Uses Flask-Caching for performance
   - CORS-enabled for cross-origin requests

5. **Configuration** (`bidsificator/config/`)
   - YAML-based configuration files
   - `config.yaml`: Main configuration (currently tracked with changes)
   - `config.example.yaml`: Example configuration template

### Key Design Patterns

- **MVC Pattern**: 
  - **Models**: Data classes in `core/` (e.g., `OptionFile.py`, `BidsFolder.py`)
  - **Views**: UI components in `ui/` (inherit from generated forms)
  - **Controllers**: Business logic in `controllers/` (e.g., `OptionController.py`)
  - **Validators**: Reusable validation logic in `core/validators.py`
- **Worker Pattern**: Long-running operations use separate worker threads to keep UI responsive
- **Configuration-Driven**: Data crawler and BIDS operations are configured via YAML files defining patterns and data types
- **Platform Compatibility**: PyEEGFormat module dynamically loads platform-specific binaries based on OS and architecture

### Dependencies

- **UI**: PyQt6 for desktop GUI
- **API**: Flask ecosystem (Flask, Flask-CORS, Flask-HTTPAuth, Flask-RESTful, Flasgger)
- **BIDS**: numpy, dicom2nifti, bids_validator for BIDS compliance
- **Build**: Poetry for dependency management, pyuic6 for UI compilation

## Working with the Codebase

ALWAYS: 
- Every development plan MUST include updating CLAUDE.md as the final task
- Always use PyQT's built-in-methods when possible

When modifying UI:
1. Edit `.ui` files in Qt Designer using `poetry run make design`
2. Compile to Python using `poetry run make build-ui`
3. Implement logic in corresponding `ui/*.py` files

When working with BIDS operations:
- Core logic is in `core/BidsFolder.py` and `core/BidsSubject.py`
- Workers handle async operations to prevent UI blocking
- Configuration patterns in YAML files define how data is discovered and organized

## MVC Architecture Review & Guidelines

### Current State (After Refactoring)
The application now follows a proper MVC pattern:
- **Models**: Core data classes (`OptionFile.py`, `BidsFolder.py`, `BidsSubject.py`)
- **Views**: PyQt6 UI components (`ui/*.py` files inheriting from generated forms)
- **Controllers**: Dedicated controller classes in `controllers/` directory
- **Validators**: Extracted validation logic in `core/validators.py`

### Refactored Components
- **OptionWindow**: Now properly separated with:
  - `OptionController`: Handles all business logic and model interactions (no observer pattern - not needed for single view)
  - `OptionWindow`: Pure view, delegates all business logic to controller
  - `validators.py`: Reusable validation functions for file extensions, paths, and patterns

### Recommended Patterns
When refactoring or adding new features:
1. **Separate concerns**: Keep business logic out of UI classes
2. **Use controllers**: Create intermediate controller classes for complex views
3. **Implement validators**: Extract validation logic to separate modules
4. **Dependency injection**: Pass models/configs to views, don't hardcode
5. **Observer pattern**: Consider implementing for model-view synchronization

### Refactoring Priority
1. **High priority**: Extract validators and business logic from views
2. **Medium priority**: Implement controller layer for complex windows
3. **Low priority**: Full observer pattern implementation
