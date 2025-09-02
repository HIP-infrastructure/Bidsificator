# Bidsificator Tests

This directory contains test scripts for various components of the Bidsificator system.

## Test Files

### Core Schema Tests
- **`test_schema.py`** - Tests BIDS schema loading, parsing, and validation
  ```bash
  poetry run python tests/test_schema.py
  ```

### Converter System Tests
- **`test_converters.py`** - Comprehensive test of the converter system
  ```bash
  poetry run python tests/test_converters.py <path_to_trc_file>
  # or
  TRC_TEST_FILE=<path> poetry run python tests/test_converters.py
  ```

### Debug Utilities
- **`debug_trc.py`** - Debug TRC file reading with neo
  ```bash
  poetry run python tests/debug_trc.py <path_to_trc_file>
  ```

- **`debug_data_range.py`** - Analyze data ranges in TRC files
  ```bash
  poetry run python tests/debug_data_range.py <path_to_trc_file>
  ```

## Usage Notes

- All TRC-related tests require a TRC file path to be provided via command line argument or `TRC_TEST_FILE` environment variable
- No hardcoded file paths are used in the tests
- Tests are designed to be portable across different systems and datasets