# SEEG Contact Labeling Feature

## Overview

The contact labeling feature allows you to annotate SEEG electrode contacts with clinical information from Excel files. This data is automatically merged into the BIDS `electrodes.tsv` files during dataset creation.

## Supported Clinical Annotations

The following clinical annotations can be added to electrodes:

### Binary Indicators (y/n/na)
- **within_ez**: Whether the contact is within the epileptogenic zone
- **rftc**: Radiofrequency thermocoagulation status
- **resected**: Whether the contact was resected

### Event Detections (with rates)
Each detection type has two columns: indicator (y/n/nd) and rate (numeric):

- **spikes_wake** / **spikes_wake_rate**: Spikes during wakefulness
- **spikes_sleep** / **spikes_sleep_rate**: Spikes during sleep
- **ripples_wake** / **ripples_wake_rate**: Ripples during wakefulness
- **ripples_sleep** / **ripples_sleep_rate**: Ripples during sleep
- **fast_ripples_wake** / **fast_ripples_wake_rate**: Fast ripples during wakefulness
- **fast_ripples_sleep** / **fast_ripples_sleep_rate**: Fast ripples during sleep

### Other
- **within_lesion**: Whether contact is within the lesion (EI value)

## Excel File Format

### Required Structure

The Excel file must have the following structure:

1. **Column Headers** (Row 1):
   - `contact`: Contact name (required)
   - Clinical annotation columns (as listed above)

2. **Format Hints** (Row 2, optional):
   - Provides format information like "y/n/na", "rate", etc.

3. **Data Rows** (Row 3+):
   - One row per contact
   - Contact names must match those in `channels.tsv`

### Example Excel Structure

| contact | within the EZ | Unnamed: 2 | spikes (wakefulness) | Unnamed: 5 | RFTC  | Resected |
|---------|---------------|------------|---------------------|------------|-------|----------|
|         | y/n/na        | EI value   | y/n/nd              | rate       | y/n/na| y/n/na   |
| Y1      | y             |            | y                   | 5.2        | y     | y        |
| Y2      | n             |            | nd                  |            | n     | n        |
| Y3      | y             |            | y                   | 12.0       | y     | n        |

**Note**: "Unnamed: X" columns are automatically created by Excel for rate/value columns that follow indicator columns.

## Usage

### Programmatic Usage

#### 1. Attach Labeling File to Subject

```python
from pathlib import Path
from bidsificator.core.BidsSubjectSchema import BidsSubject

# Create or load subject
subject = BidsSubject('patient01', dataset_path, schema_manager)

# Attach contact labeling file
labeling_file = Path('/path/to/contact_labeling.xlsx')
subject.set_contact_labeling_file(labeling_file)

# Check if labeling file is set
if subject.has_contact_labeling_file():
    print(f"Labeling file: {subject.get_contact_labeling_file()}")
```

#### 2. Generate Electrodes.tsv with Labeling Data

```python
from bidsificator.services.BidsMetadataExtractorService import BidsMetadataExtractor

extractor = BidsMetadataExtractor()

# Extract electrodes with clinical annotations
electrodes_df = extractor.extract_electrodes_tsv(
    file_path=ieeg_file_path,
    datatype='ieeg',
    contact_labeling_file=subject.get_contact_labeling_file()
)

# Save to BIDS dataset
electrodes_df.to_csv('sub-patient01_ses-pre_electrodes.tsv', sep='\t', index=False)
```

#### 3. Parse Labeling File Directly

```python
from bidsificator.services.ContactLabelingParser import ContactLabelingParser

parser = ContactLabelingParser()

# Parse Excel file
contact_data = parser.parse_file(labeling_file)

# Access annotations for specific contact
y1_annotations = contact_data['Y1']
print(f"Y1 in EZ: {y1_annotations['within_ez']}")
print(f"Y1 spikes (wake): {y1_annotations['spikes_wake']}, rate: {y1_annotations['spikes_wake_rate']}")

# Validate contact names
channel_names = ['Y1', 'Y2', 'Y3', 'Y4']
validation = parser.validate_against_channels(contact_data, channel_names)

print(f"Matched: {validation['matched']}")
print(f"Missing in labeling: {validation['missing_in_labeling']}")
print(f"Missing in channels: {validation['missing_in_channels']}")
```

### GUI Usage (Future)

The GUI will provide:
1. File picker to select contact labeling Excel file per subject
2. Display of current labeling file status
3. Validation warnings for mismatched contact names
4. Preview of clinical annotations before import

## Validation

### Contact Name Matching

The parser validates that contact names in the Excel file match those in the `channels.tsv` file:

- **Matched contacts**: Clinical annotations are merged successfully
- **Missing in labeling**: Contacts in channels.tsv without labeling data (warnings displayed)
- **Missing in channels**: Contacts in Excel file not found in channels.tsv (warnings displayed)

### Value Validation

- **Indicators**: Automatically normalized to lowercase (y/n/na/nd)
- **Rates**: Must be numeric values or empty
- **Format**: Excel file must be .xlsx or .xls

## BIDS Compliance

### Electrodes.tsv Columns

The generated `electrodes.tsv` will include:

#### Standard BIDS Columns (from specification)
- `name` (required)
- `x`, `y`, `z` (optional): Electrode coordinates
- `size` (optional): Surface area
- `hemisphere` (optional): L/R
- `group` (optional): Electrode group

#### Clinical Annotation Columns (optional, from labeling file)
- `within_ez`, `within_lesion`
- `spikes_wake`, `spikes_wake_rate`, `spikes_sleep`, `spikes_sleep_rate`
- `ripples_wake`, `ripples_wake_rate`, `ripples_sleep`, `ripples_sleep_rate`
- `fast_ripples_wake`, `fast_ripples_wake_rate`, `fast_ripples_sleep`, `fast_ripples_sleep_rate`
- `rftc`, `resected`

All clinical annotation columns are **optional** and only included if data is provided in the labeling file.

### Column Ordering

Columns are ordered as follows:
1. Standard BIDS columns (name, x, y, z, size, hemisphere, group)
2. Clinical annotation columns (alphabetically)

## Error Handling

The system handles errors gracefully:

- **Missing file**: Warning logged, returns electrodes.tsv without clinical annotations
- **Invalid format**: ValueError raised with descriptive message
- **Mismatched contacts**: Warnings displayed but processing continues
- **Parse errors**: Original electrodes.tsv returned without modifications

## Testing

Run the test suite to validate functionality:

```bash
poetry run python -m pytest tests/test_contact_labeling.py -v
```

The test suite includes:
- Excel file parsing
- Value normalization
- Contact name validation
- DataFrame merging
- Error handling

## Example Workflow

1. **Prepare Excel file** with contact annotations following the format above
2. **Create BIDS subject** in Bidsificator
3. **Attach labeling file** to subject
4. **Import iEEG data** - electrodes.tsv will automatically include clinical annotations
5. **Validate** - check for contact name mismatches
6. **Review** - verify clinical annotations in generated electrodes.tsv

## Notes

- Contact labeling files are tracked per-subject
- Files must be in Excel format (.xlsx or .xls)
- Contact names are case-insensitive (e.g., 'B02' matches 'b02')
- Missing data is represented as empty cells or 'n/a'
- Rate columns can be empty if the indicator is 'n' or 'nd'
- The feature is backward compatible - subjects without labeling files work as before
