# Bidsificator Tests

Automated tests for the Bidsificator components. Run the whole suite with:

```bash
poetry run pytest tests/ -v
# or
make test
```

## Test Files

- **`test_schema.py`** — behavioural checks on the BIDS schema manager.
- **`test_schema_sanity.py`** — the single source of truth for schema "shape"
  numbers (datatype/entity counts, per-datatype recommended-field floors). Fails
  loudly on parser regressions.
- **`test_bids_subject_schema.py`** — the schema-driven `BidsSubject`
  (creation, path building, datatype directories, metadata file generation).
- **`test_bids_filename_construction.py`** — BIDS filename construction and TSV
  filename generation (no duplicate suffixes; electrodes/coordsystem drop
  task/acq).
- **`test_bids_tsv_generation.py`** — the schema-driven TSV pipeline
  (channels/events/electrodes generation and validation).
- **`test_contact_labeling.py`** — SEEG contact-labeling parser and application.
- **`test_acquisition_numbering.py`** — acquisition entity numbering.
- **`test_validation.py`** — the schema-driven `ValidationService`.
- **`test_trc_to_edf_pyeeg.py`** — the PyEEGFormat-based TRC→EDF converter
  (mocked PyEEGFormat wrapper).
- **`test_session_form_roundtrip.py`** — GUI session-form round-trip regression
  (imports `MainWindow`; guarded by `pytest.importorskip("PyQt6")`).

## Optional integration tests

Two tests exercise a real Micromed `.TRC` file and are **skipped by default**.
To run them, point the environment variable at a TRC file:

```bash
BIDSIFICATOR_TRC_TEST_FILE=/path/to/recording.TRC poetry run pytest tests/ -v
```

Affected tests:
- `test_bids_tsv_generation.py::TestIntegrationWithRealTrcFile::test_real_trc_metadata_extraction`
- `test_trc_to_edf_pyeeg.py::TestTrcToEdfIntegration::test_real_trc_conversion`

## Notes

- Tests use pytest's `tmp_path` for filesystem work and mocks for the
  PyEEGFormat wrapper, so they are portable across machines. The only real-file
  dependency is the opt-in `BIDSIFICATOR_TRC_TEST_FILE` integration path above.
- Schema-driven tests adapt automatically to BIDS schema changes; exact counts
  are asserted only in `test_schema_sanity.py`.
