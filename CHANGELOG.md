# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multi-file batch metadata editing on the Import Files tab (UR-GUI-010, REQ-GUI-080–087). The file queue is now multi-selectable (ctrl/shift-click, Ctrl+A); with two or more files selected the metadata form switches to live batch mode where the Modality, Session, and Task dropdowns show the value the selected files share, or a "(multiple values)" placeholder where they differ, and changing one applies it to every selected file at once. Acquisition numbers are auto-reassigned across the selected files so they stay a clean sequence within their (session, modality, task) group — files you did not select keep their acquisition unchanged. Single-file edits are now consistent with this: moving one file to a different session/modality/task recomputes its acquisition for the new group (a file moved out on its own becomes acq-01) and the Acquisition field updates live as you change the dropdowns — no need to switch files and back — while an edit that stays in the same group keeps the entered value (UR-GUI-010, REQ-GUI-088; extends single-file import, UR-GUI-002). The Remove button now deletes all selected files. The per-file line-edits (Contrast Agent, Acquisition, Reconstruction) stay disabled while multiple files are selected. Single-file editing is unchanged.
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
- Grew the test suite (PR 10, test pyramid): 66 new tests across service, controller, and GUI-smoke layers, raising coverage of hand-written code from ~39% to ~45%. `test_subject_lookup_service.py` covers the CSV lookup-table parsing/validation (numeric and CUSTOM modes, per-line error messages, case-insensitive matching, template generation); `test_import_service.py` covers the display-modality mapping, acquisition auto-increment, form/data construction, duplicate detection, and per-file validation; `test_import_files_controller.py` pins the `ImportFilesController` signal contract and dialog-free logic; and `test_mainwindow_smoke.py` constructs `MainWindow` offscreen to verify the full `__init__` wiring and the per-tab mixin arrangement. A coverage floor (`--cov-fail-under=43`) is now enforced in CI so coverage can only ratchet up; the omitted paths (generated `forms/` and vendored `PyEEGFormat/`) are declared under `[tool.coverage.run]` in `pyproject.toml`.

### Changed
- Import worker subprocesses now tally a structured per-item outcome summary — each queued item recorded as imported, failed, or skipped with a human-readable reason (`str(e)` for conversion failures, never a branch-inferred label) — and send it as the terminal pipe message in place of the bare completion sentinel. A summary-level warnings channel carries failures not tied to one item (e.g. a contact-labeling file that fails to attach), and progress is emitted for every queued item so the bar always reaches 100% even when items are skipped. A pure `classify_message()` helper discriminates pipe messages by type. This is the backend groundwork for accurate import-completion reporting (UR-GUI-009, REQ-GUI-065–070); the summary is not yet surfaced in the UI.
- Import completion dialogs now report the number of files/subjects actually written from the worker's outcome summary, instead of the queued count. A partial import (some files skipped or failed) now shows the true "imported" number rather than overstating success (UR-GUI-009, REQ-GUI-072). The full failed/skipped breakdown and the completed-with-errors dialog state arrive in a later PR; the outcome summary is now carried end-to-end (worker → controller) ready for it.
- Import completion now has three distinct states (UR-GUI-009, REQ-GUI-075–078). An import where everything succeeded shows the green success dialog as before; one where some items failed or were skipped shows a "completed with errors" dialog listing each failed and skipped item with its reason (scrollable, single-line-elided with the full text on hover), plus "Copy details" and "Save…" actions that export the full UTF-8 report; one where nothing was imported is flagged as an error. The status bar gains an amber warning state, and on a partial or failed import that message now persists after the dialog is closed instead of being cleared.

### Fixed
- After a single-file import failed (subprocess error or crash), the import session stayed in its `IMPORTING` state, so every subsequent attempt was refused with "Cannot start import" and an empty message. The session is now reset on failure and the next import can start (UR-GUI-009, REQ-GUI-074).
- Import worker readers now classify each pipe message by type before any numeric comparison, so an unexpected terminal message surfaces as a normal error instead of raising inside the reader thread and hanging the GUI (no `finished`/`error` ever emitted). The workers' completion signal was also renamed off `finished` so it no longer shadows `QThread.finished` (UR-GUI-009, REQ-GUI-071/079).
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
- The Import Subjects lookup table (subject anonymization) now applies regardless of order. Previously `set_lookup_table` only stored the mapping; it was applied solely at crawl time, so loading the CSV *after* clicking Parse left the already-parsed subjects showing their original folder names (and importing them under those names) — it looked like the lookup "wasn't read". `set_lookup_table` now re-applies the mapping to already-loaded subjects in place (and clearing it reverts them), preserving any per-subject file edits since it re-maps rather than re-crawls. The mapping/display formatting is shared between crawl-time and reload via a new `DataCrawlerService.format_mapped_subject`, and the in-place update is `SubjectDataModel.reapply_subject_mapping`.
- Validation now checks BIDS-inheritance-located companion files again. The `inherit: true` association fallback in `FileRuleValidator._find_associated_file` called `_get_inheritance_aware_entities` on its `BidsSubject` helper, but the method moved to `SubjectSidecarGenerator` in the collaborator split without a delegator on `BidsSubject`; the resulting `AttributeError` was swallowed by a bare `except`, so inheritance-located companions (e.g. a session-level `electrodes.tsv` describing subject-level data) were silently never checked. `BidsSubject` now delegates `_get_inheritance_aware_entities` to the sidecar generator, restoring the fallback.

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
- Split the `ValidationService` god class (PR 9a of the god-class split). The 1552-line `services/ValidationServiceSchema.py` now delegates to a new `bidsificator/validation/` package: `report.py` (the `ValidationError`/`ValidationResult` result types), `rules_files.py` (`FileRuleValidator` — dataset-root, subject-structure, datatype-directory, filename, and schema-association checks), `rules_metadata.py` (`MetadataRuleValidator` — dataset_description.json + JSON-sidecar checks and the schema selector-expression evaluation), and `_parsing.py` (shared BIDS-filename parsing helpers). `ValidationService` stays a thin facade at the same import path and re-exports `ValidationError`/`ValidationResult`, so no caller changes and the existing tests pass untouched. Behavior is unchanged.
- Split the `BidsSubject` god class (PR 9b of the god-class split). The 1263-line `core/BidsSubjectSchema.py` file-writing cluster moved to two collaborators: `core/subject_file_writer.py` (`SubjectFileWriter` — the `add_file` pipeline: analysis, conversion, suffix detection, entity validation, target-path construction, copying the data file) and `core/subject_sidecar_generator.py` (`SubjectSidecarGenerator` — the JSON sidecar and the channels/events/electrodes/coordsystem/optodes companion files, plus the metadata default-value strategy). Both extend a small `core/subject_component.py` base that reads the owning subject's live state (id/path, optional metadata, contact-labeling file) via a back-reference, so a rename or metadata update is always reflected. `BidsSubject` (now 412 lines) keeps its identity/container surface and thin delegating methods for the public and historical `_`-prefixed API that callers and tests use, so no caller changes and the existing tests pass untouched. Behavior is unchanged.
- Split the `MainWindow` god class (PR 9c of the god-class split). The 1429-line `ui/MainWindow.py` had every tab's slots and helpers in one class; each tab's logic moved to its own file under a new `ui/tabs/` package as a mixin: `participants_tab.py` (`ParticipantsTabMixin` — subject creation and the file-tree context-menu operations: validate/rename/delete), `import_files_tab.py` (`ImportFilesTabMixin` — the per-file metadata form, file list, modality/session/subject handling, and file import), and `import_subjects_tab.py` (`ImportSubjectsTabMixin` — subject parsing, the subject list + embedded FileEditor sync, the lookup table, and batch import). `MainWindow` (now 374 lines) is composed from the three mixins and keeps window setup, the controller wiring, the cross-tab signal handlers, dataset create/open, the validation state, and the status-bar handlers. Mixins were chosen so `self` stays the live window: the slot bodies (and their dialog parents) and all the Qt signal connections are unchanged, so behavior is identical and the tests pass untouched. Two instance attributes were renamed off the double-underscore form (`__browse_folder_path_memory` → `_browse_folder_path_memory`, `__ImportSubjectFileEditor` → `_import_subject_file_editor`) so the mixins can reach them without name mangling. This is an interim structural split; a later change will regenerate the `.ui` into per-tab widgets for true encapsulation.
- Decoupled `FileEditorController` from the UI (controller-dialog sweep, part 1 of 4 — continues the 8b pattern for the remaining controllers). The "Other" task option no longer opens a `QInputDialog` or shows `QMessageBox` warnings from inside the controller: `handle_task_selection` is replaced by `add_custom_task(new_task, current_tasks)`, which the `FileEditor` view calls after gathering the task-name text itself; empty/invalid names come back via a new `operation_failed(title, message)` signal that the view renders. `FileEditorController` no longer imports `QInputDialog`/`QMessageBox`. Behavior is preserved.
- Decoupled `PatientTableController` from the UI (controller-dialog sweep, part 2 of 4). The subject-table controller no longer imports `QInputDialog`/`QMessageBox`: the new-key name is now gathered by the `PatientTableWidget` view and passed in (`add_key_after`/`add_key_before` take a `key_name` argument), and the remove-key confirmation prompt moved to the view (the reserved `subject_id` column is still guarded in the controller and reported without a prompt, preserving the original order). The invalid/duplicate subject-ID, duplicate-key, and cannot-remove warnings are now emitted as `operation_failed(title, message)`. Also replaced three silent `except Exception: return False` blocks (including the one with a `# Log error appropriately in production` TODO) with `logger.exception(...)` so field-update/add-key/remove-key failures are recorded. Behavior is preserved.
- Decoupled `ImportFilesController` from the UI (controller-dialog sweep, part 3 of 4). The single-file import controller no longer imports `QFileDialog`/`QMessageBox`. The file-selection dialog moved to the `import_files_tab` view (`add_multiple_files` there now opens the picker and calls the new `add_files_from_paths(files, form_defaults)`); the results summary, the "No Selection"/"No Dataset"/"Import in Progress"/"Cannot start import" warnings (now `operation_failed`), and the "Import Complete"/"Import Failed" modals (now rendered by `MainWindow` from the existing `import_completed`/`import_failed` signals) all moved to the view. The two confirmations moved to the view behind controller predicates: the subject-change prompt via `needs_subject_change_confirmation(new_subject)`, and the electrodes.tsv-regeneration prompt via `import_would_regenerate_electrodes()`. Deleted the dead `browse_single_file` method (unreferenced since the browse button was removed in the PR 8a MVC migration) and three now-unused `MainController` wrappers (`add_multiple_files`, `remove_selected_import_file`, `update_import_files_subject`). Behavior is preserved, with one incidental fix: cancelling the electrodes-regeneration prompt no longer leaves the import session stuck in the `IMPORTING` state (the old code called `model.start_import()` before that prompt and did not roll back on cancel).
- Decoupled `ImportSubjectsController` from the UI (controller-dialog sweep, part 4 of 4 — completes the sweep; all six controllers are now free of `QInputDialog`/`QFileDialog`/`QMessageBox`). Warnings (parse-failure, the batch-import pre-check failures, lookup-table validation/parse errors) are now emitted as `operation_failed(title, message)`, and informational messages (lookup-table loaded preview, "all subjects skipped") as a new `operation_info(title, message)`; both are rendered by `MainWindow`. The "Import Complete"/"Import Failed" modals moved to `MainWindow` (via the existing `import_completed`/`import_failed` signals). The remove-subjects confirmation moved to the `import_subjects_tab` view. The 3-button "Subject Conflicts Detected" dialog also moved to the view: `start_batch_import(task, conflict_resolver)` now takes a callback (threaded through `MainController.start_subjects_import`) that the view supplies to return "overwrite"/"skip"/"cancel", so `start_batch_import`'s flow is otherwise unchanged. The save-template file dialog moved to the view; `create_lookup_template` is replaced by the UI-free `save_lookup_template(file_path) -> (success, message)`. Behavior is preserved.
- Split the Import Subjects tab into its own `.ui` and QWidget (PR 9d.1 of the per-tab UI split — the true encapsulation deferred from the PR 9c mixin split). Its widget subtree moved out of the monolithic `forms/MainWindow.ui` into a new `forms/ImportSubjectsTab.ui`, and the `ImportSubjectsTabMixin` became a self-contained `ImportSubjectsTab(QWidget)` that owns its widgets, builds its own embedded `FileEditor`, wires its own `ImportSubjectsController` signals, and renders its own dialogs (parented to the tab). Dependencies are injected by the host (`MainController`, the shared `StatusBarManager`, and getter/setter callbacks for the shared "last browsed folder" memory); `MainWindow` constructs the tab and inserts it at index 2 at runtime. The subjects-only slots and the subjects controller-wiring block were removed from `MainWindow`; the shared `operation_failed`/`import_failed`/`dialog_dismissed` slots stay (still used by the Import Files tab). `make build-ui` now regenerates the per-tab `_ui.py` via a pattern rule and `make design` opens all forms. Behavior is preserved.
- Split the Import Files tab into its own `.ui` and QWidget (PR 9d.2 of the per-tab UI split). Its widget subtree moved from `forms/MainWindow.ui` into a new `forms/ImportFilesTab.ui`, and `ImportFilesTabMixin` became a self-contained `ImportFilesTab(QWidget)` owning the per-file metadata form, the file list, the subject dropdown, modality/session/task handling, the contact-labeling file, and the file import — wiring its own `ImportFilesController` signals and rendering its own dialogs. Same host-injected dependencies as 9d.1; `MainWindow` inserts it at index 1 (ascending order, before the subjects tab, so `insertTab` doesn't clamp). The cross-tab subject dropdown is refreshed via a new `ImportFilesTab.refresh_subject_dropdown()` that the host calls on subject changes (formerly `update_subject_names_dropDown`); the lazy connect-on-refresh of the subject-combo signals is preserved. With both import tabs now owning their dialogs, `MainWindow` sheds its last import slots (`_on_operation_failed`/`_on_import_failed`/`_on_dialog_dismissed`/`_on_file_import_*`/`_show_file_import_failed_dialog`) — it is now purely the host plus the Participants tab and the file-tree/validation chrome. `test_session_form_roundtrip.py` now targets `ImportFilesTab._set_session_combobox_text`. Behavior is preserved.
- Split the Participants tab into its own `.ui` and QWidget and finished the per-tab split (PR 9d.3 — completes 9d; the true per-tab encapsulation deferred from PR 9c is done). The Participants widget subtree (and the `PatientTableWidget` promotion) moved from `forms/MainWindow.ui` into a new `forms/ParticipantsTab.ui`, and `ParticipantsTabMixin` became a self-contained `ParticipantsTab(QWidget)` owning subject creation and the `PatientTableWidget` (which keeps its own `PatientTableController`); it re-emits `subject_updated` and exposes `subject_controller` and `refresh_table(path)` for the host. `MainWindow.ui` is now just the window shell + an empty tab widget; `MainWindow` no longer inherits any tab mixin — it constructs all three `QWidget` tabs and inserts them at indices 0/1/2 at runtime. The file-tree browser and BIDS-validator button live in the left splitter pane (outside the tab widget), so their handlers stay on `MainWindow` as window chrome; the tree's rename/delete operations reach the subject controller through `ParticipantsTab.subject_controller`. `ui/tabs/` now holds three QWidget tabs and no mixins. Behavior is preserved.

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
- Dead `ImportFilesController.get_ui_requirements_for_modality` and its now-orphaned `FileDetectionService` import. The method had no callers and called `FileDetectionService.get_modality_requirements()`, which does not exist (it would have raised `AttributeError` if ever reached); the live modality-UI path is `FileEditorController.get_modality_ui_requirements` via `FileDetectionService.get_modality_info(...).ui_requirements`.

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
