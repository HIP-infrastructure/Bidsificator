# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Continuous integration workflow running the test suite on Python 3.11–3.13.
- `make test` and `make lint` targets.
- This CHANGELOG.
- Shared `tests/conftest.py` fixture; committed `tests/test_schema_sanity.py`.
- Application-wide logging (`bidsificator/core/logging_config.py`): the GUI, the
  API, and each import worker subprocess configure the root logger, and modules
  now log through `logging.getLogger(__name__)` instead of `print()`.
- Ruff linting (`E`, `F`, `W`, `I`, `B`, `UP`) and pytest coverage
  (`--cov=bidsificator`) run in CI on every push/PR. Configuration lives in
  `pyproject.toml`; generated Qt UI modules and the vendored PyEEGFormat tree are
  excluded.

### Fixed
- Resolved the full existing ruff surface (~3.3k findings): whitespace and
  import ordering, modernized type hints (PEP 585/604) and `super()` calls,
  narrowed two bare `except:` clauses, chained re-raises with `from`, and fixed
  a duplicate `get_subject_id` method and a broken `__main__` runner in
  `tests/test_bids_subject_schema.py` that referenced undefined names.
- Channels TSV validation now flags a missing required `name`/`type`/`units`
  column. Previously the required-column set was empty for `channels.tsv`
  (requirement levels weren't wired up from the schema), so missing required
  columns went undetected.
- README inaccuracies: the supported Python range is now stated as 3.11–3.13
  (was 3.10–3.12), the License section points to the actual `LICENSE`, and the
  broken quick-start link now targets an in-page anchor. Also embedded the
  project logo at the top.
- Import workers no longer hang the GUI forever when their subprocess dies
  without reporting (crash / OOM kill). `run()` now polls the pipe with a
  timeout and detects a dead child, emitting an `error` signal within ~5 s.
- A failed import (subject not found, or a subprocess error) now surfaces an
  error dialog and status-bar message instead of the "Import complete" success
  dialog. Previously the workers emitted `finished` unconditionally and the
  controllers hardcoded `"success": True`.
- Fixed a latent crash on the Import Files add path: `ImportFilesController.add_multiple_files` and `browse_single_file` called `FileDetectionService.get_all_supported_extensions()` / `get_file_filters()` on the class rather than an instance (`TypeError`). These paths were dead until now (the view reimplemented adding), so the bug had never surfaced; they are the live add path after the state migration below.

### Changed
- Made the test suite trustworthy: removed hardcoded personal file paths (the
  real-TRC integration tests are now opt-in via `BIDSIFICATOR_TRC_TEST_FILE`),
  converted print/return-based placeholder tests into real assertions, and
  updated stale assertions to match current BIDS-correct behavior (e.g.
  electrodes/coordsystem filenames omit `task`/`acq`; trigger events use a
  generic `trial_type` with the code in the `value` column).
- `config.yaml` is now user-local and git-ignored; it is auto-created from
  `config.example.yaml` on first run through a shared
  `BidsUtilityFunctions.get_config_path()` helper (previously the file was
  tracked and four call sites hard-coded the path, which would `FileNotFoundError`
  on a fresh clone once untracked).
- Migrated packaging metadata to PEP 621 `[project]` (Poetry 2.x); filled in the
  previously empty `description`, corrected the license to the SPDX identifier
  `Apache-2.0`, and added the repository URL, keywords, and classifiers.
  Dependencies stay in `[tool.poetry.dependencies]` (declared `dynamic`), so the
  lockfile and resolved versions are unchanged.
- Deduplicated the import worker processors. The modality dispatch was
  copy-pasted across `processBidsFiles` and `processBidsSubjects` (and a second
  time within the latter); it now lives once in a new
  `workers/import_processor.py` (`resolve_datatype_and_suffix` +
  `add_file_to_subject`), which also owns the `ANATOMICAL_MODALITIES` set (was
  duplicated in both workers) and the progress sentinels (absorbing
  `workers/protocol.py`). Renamed the misspelled `BidsFilesProcss.py` →
  `BidsFilesProcess.py`. Behavior is unchanged, including the deliberate
  difference between the two paths (the subjects path applies one shared,
  schema-required task entity; the files path takes task per file).
- Import Files tab now uses a single source of truth (PR 8a of the MVC migration). `MainWindow` previously kept a parallel `__import_files_data` dict (~40 usages) and reimplemented add / remove / modality-detection / acquisition logic, syncing to `ImportFilesController` + `ImportSessionModel` only at import time — the dual-source-of-truth that caused the #15 session/acquisition corruption. The view now delegates add, remove, and subject-change to the controller and reads file state from the model; the file list, current subject, and contact-labeling file live only in the model. The view keeps just the form load/save *timing* (a genuine view concern), now operating on the model. Deleted `set_files_data`/`load_from_legacy_data` and the view's duplicated `_create_file_data`/`_process_selected_files`/`_is_duplicate_file`/`detect_modality_from_file`/`get_next_acquisition_number`/`add_file_to_import_data`/`_select_files_for_import`/`_show_import_results`/`update_selection_after_removal` helpers. Behavior is preserved, including the empty-session round-trip guarding #15; see the related fix above. Modality auto-detection now runs solely through the shared `FileDetectionService` (the view's duplicate `detect_modality_from_file` is gone); for every file type this tool detects — iEEG (`.trc`/`.edf`/`.vhdr`/`.bdf`), anatomical (`.nii`), photos — the resulting modality is unchanged.
- Decoupled `DatasetController` from the UI (PR 8b of the MVC migration). It no longer imports `QFileDialog`/`QInputDialog`/`QMessageBox` or the inverted `..ui.ValidationResultsDialog`; it is now a `QObject` that emits `operation_failed(title, message)`, `validation_started(message)`, and `validation_finished(result)`. `MainWindow` connects those to the dialogs and now gathers the folder/name inputs for dataset create/open itself (`create_new_dataset`/`load_existing_dataset` take those as arguments). Behavior is preserved; the only cosmetic change is that a validation-time exception now surfaces as a warning box rather than a critical box.
- Moved the file-deletion filesystem work out of the view. `MainWindow.delete_files_from_tree` now delegates the `os.remove` loop to `DatasetModel.delete_files` (through `DatasetController`/`MainController`) and keeps only the confirmation prompt and the result dialogs; the model returns `(deleted_paths, failed)` for the view to report.
- Deduplicated the modality-dropdown display mapping. The `datatype_mapping` dict was copy-pasted in `MainWindow` and `FileEditor`; both now read a single `MODALITY_DISPLAY_MAPPING` in `core/bids_constants.py`.

### Removed
- Dead `core/BidsSubject.py` module (376 lines, superseded by
  `BidsSubjectSchema`) and dead code in `MainWindow` (the unused browse-file
  methods, the unreachable `on_worker_finished` handler with its `__worker`/
  `__subject_data` attributes, and stale/duplicate imports).
- Unused `flask-restful` dependency.
- Leftover unused `ImportBidsFilesWorker` import in `MainWindow` (workers are
  instantiated in the controllers, not the view).
- Broken API-only `.devcontainer/` (its `api.Dockerfile` copied a nonexistent
  `requirements.txt` and pinned Python 3.10, unsupported since the Poetry
  migration).
- The two unused MNE/neo-based TRC converters (`trc_to_edf.py`, `trc_to_brainvision.py`). TRC→EDF is handled by the bundled PyEEGFormat converter, which was already the only one ever selected: the registry returns the highest-priority converter and nothing requests a specific target format, so the MNE EDF *fallback* only fired on platforms with no PyEEGFormat wrapper and the `.vhdr` BrainVision converter was never reachable at all. Removing them drops the `mne`, `neo`, `quantities`, `edfio`, and `pybv` dependencies (used only by those two files and by `mne.export`'s runtime backends). New converters can be added later if a format PyEEGFormat does not cover comes up.
- The unused `FileAnalysis` dataclass in `converters/base.py` — a stale duplicate of the canonical schema-driven `core/file_analysis.py`; it was only re-exported from `converters/__init__.py`, never constructed.

### Security
- The `bidsificator-api` server no longer starts with the Werkzeug debugger
  enabled and now binds to `127.0.0.1` by default, closing an accidental
  stack-trace / debugger-PIN RCE exposure if the (dormant) API is ever launched.
  Debug mode, host, and port are explicit opt-ins via `BIDSIFICATOR_API_DEBUG`,
  `BIDSIFICATOR_API_HOST`, and `BIDSIFICATOR_API_PORT`.

## [1.13.0] — 2026-07-20
- Fix import session/acquisition corruption, add app logo. (#15)

## [1.12.0] — 2026-01-21
- Update dependencies.

## [1.11.0] — 2025-12-05
- Add import of clinical CSV values. (#14)

## [1.10.0] — 2025-10-01
- Fix some UI bugs. (#13)

## [1.9.0] — 2025-09-11
- Update BIDS schema. (#11)

## [1.8.1] — 2025-09-10
- Fix look-up tables and some UI issues. (#10)

## [1.8.0] — 2025-09-09
- Adapt to the BIDS schema. (#9)

## [1.5.3] — 2025-09-02
- Use a Python file for metadata info instead of the pyproject file. (#8)

## [1.5.2] — 2025-09-01
- Add a Help menu / About dialog sourcing information from project metadata. (#7)

## [1.5.1] — 2025-09-01
- Permissions fixes.

## [1.5.0] — 2025-08-29
- v1.5.0 release. (#6)

## [1.0.1] — 2025-08-12
- New `.so` binaries and assorted fixes. (#5)

## [1.0.0] — 2024-09-25
- Initial tagged release.

<!--
Note: v1.6 and v1.7 were never tagged — the jump from v1.5.x to v1.8.0 is
historical and intentional.
-->

[Unreleased]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.13.0...HEAD
[1.13.0]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.12.0...v1.13.0
[1.12.0]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.11.0...v1.12.0
[1.11.0]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.10.0...v1.11.0
[1.10.0]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.8.1...v1.9.0
[1.8.1]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.5.3...v1.8.0
[1.5.3]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.5.2...v1.5.3
[1.5.2]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.0.1...v1.5.0
[1.0.1]: https://github.com/HIP-infrastructure/Bidsificator/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/HIP-infrastructure/Bidsificator/releases/tag/v1.0.0
