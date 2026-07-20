# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Scope: this file is checked into the code repo and travels with it — a fresh
> clone or CI run gets everything here without needing the Knowledge Hub. It
> holds **actionable, in-repo coding guidance**. Deep reference material
> (metadata default catalogs, validator warning catalog, parser debugging) lives
> in the Knowledge Hub spec appendices and is linked below, so it can be
> versioned and dated rather than drifting here.

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

# Run tests
poetry run pytest
```

## Changelog

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com). **Every
PR with a user- or developer-visible effect adds its entry under `[Unreleased]`
in the same PR** — in the matching subsection (Added / Changed / Deprecated /
Removed / Fixed / Security), not as a later cleanup. On release, rename
`[Unreleased]` to the version + date, open a fresh empty `[Unreleased]`, and add
the version's compare link at the bottom of the file. Purely internal no-op
changes (typo fixes, comments, formatting) may skip it.

## Architecture

MVC with a schema-driven core. See the Knowledge Hub for the full picture:
`Bidsificator-knowledge-hub/knowledge/architecture.md`.

- **Controllers** (`bidsificator/controllers/`): business-logic coordination
  (`MainController` orchestrates `DatasetController`, `ImportFilesController`,
  `ImportSubjectsController`, `FileEditorController`, `PatientTableController`,
  `OptionController`).
- **Models** (`bidsificator/models/`): `DatasetModel`, `ImportFileModel`,
  `ImportSessionModel`, `SubjectDataModel`.
- **Views** (`bidsificator/ui/`): `MainWindow`, `FileEditor`,
  `PatientTableWidget`, `OptionWindow`. Generated from `.ui` files in
  `bidsificator/forms/` — run `poetry run make build-ui` after changes.
- **Services** (`bidsificator/services/`): `DataCrawlerService`,
  `FileDetectionService`, `ImportService`, `ValidationService`.
- **Core** (`bidsificator/core/`): `BidsFolder`, `BidsSubject`, `DataCrawler`,
  `filename_builder`, and `schema/` (`parser`, `models`, `schema_manager`).
- **Workers** (`bidsificator/workers/`): background processing on `QThread` with
  `multiprocessing` for CPU-bound work.

### Configuration
Config files in `bidsificator/config/`: `config.yaml` (active),
`config.example.yaml` (template), site-specific configs (e.g. `config.lyon.yaml`).

### Dependencies
PyQt6 (GUI), NumPy, dicom2nifti (DICOM conversion), bids_validator (compliance),
Flask ecosystem (API server).

## Schema-Driven Architecture — Core Principles

These are the rules to follow when writing code. The detailed catalogs they
summarize live in the Knowledge Hub (linked at the bottom).

- **Never hardcode BIDS metadata fields, entities, suffixes, or the BIDS
  version.** Extract everything from the schema at
  `bidsificator/schema/bids_schema.json` via the singleton
  `BidsSchemaManager.get_instance()`. Use `get_entity_order()`,
  `get_default_suffix_for_datatype()`, and `schema_manager.get_bids_version()`.

- **Metadata type safety (prevents `JSON_SCHEMA_VALIDATION_ERROR`):**
  - String fields may default to `"n/a"`.
  - Numeric, boolean, array, and enum fields MUST return `None` (omit the key)
    when unknown — never a string like `"n/a"`.
  - Always filter `None` before serializing:
    `{k: v for k, v in metadata.items() if v is not None}`.

- **Fix root causes, never skip validation.** Validator WARNINGs about missing
  RECOMMENDED fields are expected and correct when data is genuinely
  unavailable — omit the field, don't insert a placeholder to silence them.

- **Don't hunt for magic numbers here.** Schema shape (datatype count, entity
  count, per-datatype recommended-field counts) is asserted by
  `tests/test_schema_sanity.py`, which is the single source of truth and fails
  loudly on parser regressions. Run `poetry run pytest tests/test_schema_sanity.py`
  rather than trusting a number written in prose.

### Deeper reference (Knowledge Hub)

| Topic | Location |
|-------|----------|
| Metadata default-value strategy, MRI field categories | `specs/CORE/bids_subject_schema/design.md` |
| Validator warning/error catalog, selector evaluation | `specs/VALID/validation_service/design.md` |
| Parser internals, debugging checklist, gotchas | `specs/SCHEMA/schema_parser/design.md` |
| System architecture, data flows | `knowledge/architecture.md` |

Paths are relative to `Bidsificator-knowledge-hub/` (the sibling repo in the
project workspace).
