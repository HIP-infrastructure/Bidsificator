"""File / directory-structure validation rules.

`FileRuleValidator` owns the dataset-root, subject-structure, datatype-directory,
filename, and schema-association checks. It holds the schema manager, an
inheritance-aware `BidsSubject` helper (for association lookups), and a reference
to the `MetadataRuleValidator` for the two places where file checks descend into
metadata checks (dataset_description.json and per-file JSON sidecars).
Extracted from the ValidationService god class.
"""

from pathlib import Path
from typing import Any

from bidsificator.core.bids_constants import ENTITY_ORDER
from bidsificator.validation._parsing import (
    extract_suffix_from_filename,
    parse_entities_from_filename,
    parse_filename,
)
from bidsificator.validation.report import ValidationError, ValidationResult


class FileRuleValidator:
    """Schema-driven checks for dataset structure, filenames, and associations."""

    def __init__(self, schema, schema_helper, metadata_validator):
        self.schema = schema
        # BidsSubject helper reused for inheritance-aware association lookups.
        self.schema_helper = schema_helper
        # File checks descend into metadata checks in two places.
        self.metadata = metadata_validator

    def validate_dataset_root(self, dataset_path: Path) -> tuple[list[ValidationError],
                                                                list[ValidationError],
                                                                list[ValidationError]]:
        """Validate root-level dataset files"""
        errors = []
        warnings = []
        info = []

        # Check required files from schema
        required_files = self._get_required_files_from_schema()
        for req_file in required_files:
            file_path = dataset_path / req_file
            if not file_path.exists():
                errors.append(ValidationError(
                    str(file_path),
                    f"Missing required file: {req_file}",
                    "error",
                    "missing-required-file"
                ))
            else:
                # Validate dataset_description.json content
                if req_file == "dataset_description.json":
                    desc_errors, desc_warnings = self.metadata.validate_dataset_description(file_path)
                    errors.extend(desc_errors)
                    warnings.extend(desc_warnings)

        # Validate participants.tsv if it exists
        participants_file = dataset_path / "participants.tsv"
        if participants_file.exists():
            tsv_errors = self._validate_participants_tsv(participants_file)
            errors.extend(tsv_errors)

        # Check recommended files from schema
        recommended_file_groups = self._get_recommended_file_groups_from_schema()

        missing_recommended = []
        for file_group in recommended_file_groups:
            # Check if at least one file from the group exists
            group_found = any((dataset_path / f).exists() for f in file_group)
            if not group_found:
                # Add only the first/preferred option to missing list for clarity
                missing_recommended.append(file_group[0])

        if len(missing_recommended) == len(recommended_file_groups):
            warnings.append(ValidationError(
                str(dataset_path),
                "Missing all recommended files: README, participants.tsv, CHANGES",
                "warning",
                "missing-recommended-files"
            ))
        elif missing_recommended:
            info.append(ValidationError(
                str(dataset_path),
                f"Missing some recommended files: {', '.join(missing_recommended)}",
                "info",
                "partial-recommended-files"
            ))

        return errors, warnings, info

    def _validate_participants_tsv(self, tsv_path: Path) -> list[ValidationError]:
        """Validate participants.tsv content"""
        errors = []

        try:
            import csv
            with open(tsv_path, encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                rows = list(reader)

                if 'sex' in reader.fieldnames:
                    for _i, row in enumerate(rows, start=2):  # Start at 2 for header row
                        sex_value = row.get('sex', '').strip()
                        if sex_value and sex_value not in ['M', 'F', 'm', 'f', 'male', 'female']:
                            # Check if it's the problematic 'M/F' format
                            if '/' in sex_value:
                                errors.append(ValidationError(
                                    str(tsv_path),
                                    "A value in a column did not match the acceptable type for that "
                                    "column headers specified format. "
                                    f"('{sex_value}')",
                                    "error",
                                    "TSV_VALUE_INCORRECT_TYPE"
                                ))

        except Exception as e:
            errors.append(ValidationError(
                str(tsv_path),
                f"Error reading participants.tsv: {e}",
                "error",
                "tsv-read-error"
            ))

        return errors

    def validate_subject_structure(self, subject_path: Path, errors: list[ValidationError],
                                   warnings: list[ValidationError], info: list[ValidationError]) -> bool:
        """Validate subject directory structure and return whether it has data"""
        has_data = False

        # Check direct datatypes (no session)
        for datatype in self.schema.datatypes:
            datatype_dir = subject_path / datatype
            if datatype_dir.exists() and datatype_dir.is_dir():
                has_data = True
                dt_errors, dt_warnings, dt_info = self._validate_datatype_directory(datatype_dir, datatype)
                errors.extend(dt_errors)
                warnings.extend(dt_warnings)
                info.extend(dt_info)

        # Check sessions
        for item in subject_path.iterdir():
            if item.is_dir() and item.name.startswith('ses-'):
                has_data = True
                session_id = item.name.replace('ses-', '')

                # Validate session ID format
                if not self.schema.validate_entity_value('ses', session_id):
                    errors.append(ValidationError(
                        str(item),
                        f"Invalid session ID format: {item.name}",
                        "error",
                        "invalid-session-format"
                    ))

                # Check datatypes within session
                for datatype in self.schema.datatypes:
                    datatype_dir = item / datatype
                    if datatype_dir.exists() and datatype_dir.is_dir():
                        dt_errors, dt_warnings, dt_info = self._validate_datatype_directory(datatype_dir, datatype)
                        errors.extend(dt_errors)
                        warnings.extend(dt_warnings)
                        info.extend(dt_info)

        return has_data

    def _validate_datatype_directory(self, datatype_dir: Path, datatype: str) -> tuple[list[ValidationError],
                                                                                      list[ValidationError],
                                                                                      list[ValidationError]]:
        """Validate files within a datatype directory"""
        errors = []
        warnings = []
        info = []

        dt = self.schema.get_datatype(datatype)
        if not dt:
            errors.append(ValidationError(
                str(datatype_dir),
                f"Unknown datatype: {datatype}",
                "error",
                "unknown-datatype"
            ))
            return errors, warnings, info

        # Get expected extensions for this datatype
        expected_extensions = (
            self.schema.file_registry.get_supported_extensions(datatype)
            if hasattr(self.schema, 'file_registry')
            else []
        )

        # Track files and their sidecars
        data_files = []
        metadata_files = []

        # Scan all files in directory
        for file_path in datatype_dir.glob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                if file_path.suffix in ['.json', '.tsv', '.bval', '.bvec']:
                    metadata_files.append(file_path)
                else:
                    data_files.append(file_path)

        # Validate each data file
        for file_path in data_files:
            # Validate filename
            filename_result = self.validate_filename(file_path.name, datatype)
            errors.extend(filename_result.errors)
            warnings.extend(filename_result.warnings)

            # Check extension
            if expected_extensions and file_path.suffix not in expected_extensions:
                warnings.append(ValidationError(
                    str(file_path),
                    f"Unexpected extension {file_path.suffix} for datatype {datatype}",
                    "warning",
                    "unexpected-extension"
                ))

            # Check for JSON sidecar
            json_sidecar = file_path.with_suffix('.json')
            if not json_sidecar.exists():
                warnings.append(ValidationError(
                    str(file_path),
                    "Missing JSON sidecar",
                    "warning",
                    "missing-sidecar"
                ))
            else:
                # Validate JSON sidecar content
                sidecar_results = self.metadata.validate_json_sidecar(json_sidecar, datatype)
                # Separate sidecar results by severity
                for result in sidecar_results:
                    if result.severity == "error":
                        errors.append(result)
                    elif result.severity == "warning":
                        warnings.append(result)
                    elif result.severity == "info":
                        info.append(result)

            # Check for required associated files based on schema associations
            assoc_errors = self._check_schema_associations(file_path, datatype)
            errors.extend(assoc_errors)

        return errors, warnings, info

    def validate_filename(self, filename: str, datatype: str | None = None,
                         expected_entities: dict[str, str] | None = None) -> ValidationResult:
        """
        Validate BIDS filename using schema rules

        Args:
            filename: Filename to validate
            datatype: Optional datatype for context-specific validation
            expected_entities: Optional expected entities for comparison

        Returns:
            ValidationResult with filename validation
        """
        errors = []
        warnings = []
        info = []

        path = Path(filename)
        name = path.stem  # Remove extension

        # Parse filename into components
        entities, suffix = parse_filename(name)

        # Validate basic filename structure
        if 'sub' not in entities:
            errors.append(ValidationError(
                filename,
                "Missing required 'sub-' entity",
                "error",
                "missing-subject"
            ))

        # Validate entity values against schema
        for entity_key, entity_value in entities.items():
            if not self.schema.validate_entity_value(entity_key, entity_value):
                errors.append(ValidationError(
                    filename,
                    f"Invalid value '{entity_value}' for entity '{entity_key}'",
                    "error",
                    "invalid-entity-value"
                ))

        # Validate against datatype rules if provided
        if datatype and datatype in self.schema.datatypes:
            dt_errors, dt_warnings = self._validate_filename_against_datatype(
                filename, entities, suffix, datatype
            )
            errors.extend(dt_errors)
            warnings.extend(dt_warnings)

        # Check entity order
        order_warnings = self._check_entity_order(filename, entities)
        warnings.extend(order_warnings)

        # Compare with expected entities if provided
        if expected_entities:
            comparison_info = self._compare_entities(filename, entities, expected_entities)
            info.extend(comparison_info)

        is_valid = len(errors) == 0
        message = "Valid BIDS filename" if is_valid else f"Invalid filename ({len(errors)} error(s))"

        return ValidationResult(
            is_valid=is_valid,
            message=message,
            errors=errors,
            warnings=warnings,
            info=info
        )

    def _validate_filename_against_datatype(
        self, filename: str, entities: dict[str, str], suffix: str | None, datatype: str
    ) -> tuple[list[ValidationError], list[ValidationError]]:
        """Validate filename against suffix-specific schema rules"""
        errors = []
        warnings = []

        if not suffix:
            return errors, warnings

        # Find the specific rule that applies to this datatype + suffix combination
        matching_rule = self._find_matching_file_rule(datatype, suffix)

        if not matching_rule:
            # If no specific rule found, fall back to basic validation
            warnings.append(ValidationError(
                filename,
                f"No specific validation rule found for {datatype}/{suffix}",
                "warning",
                "no-validation-rule"
            ))
            return errors, warnings

        # Create mapping from entity keys to entity names
        key_to_name = {}
        for entity_key, entity_obj in self.schema.entities.items():
            key_to_name[entity_key] = entity_obj.name.lower().replace(' ', '').replace('-', '')

        # Get allowed and required entities from the matching rule
        rule_entities = matching_rule.get('entities', {})

        # Use existing entity mapping to convert schema names to keys
        name_to_key = {}
        for entity_key, entity_obj in self.schema.entities.items():
            # Convert entity name to comparable format
            entity_name = entity_obj.name.lower().replace(' ', '').replace('-', '')
            name_to_key[entity_name] = entity_key

        allowed_entity_keys = set()
        required_entity_keys = set()

        for schema_entity_name, requirement in rule_entities.items():
            # Convert schema entity name to key using existing mappings
            comparable_name = schema_entity_name.lower().replace(' ', '').replace('-', '')
            entity_key = name_to_key.get(comparable_name, schema_entity_name)

            allowed_entity_keys.add(entity_key)
            if requirement == 'required':
                required_entity_keys.add(entity_key)

        # Check allowed entities
        for entity_key in entities:
            if entity_key not in allowed_entity_keys:
                # Get entity name for error message
                entity_name = key_to_name.get(entity_key, entity_key)
                errors.append(ValidationError(
                    filename,
                    f"Entity '{entity_key}' ('{entity_name}') not allowed for {datatype}/{suffix}",
                    "error",
                    "disallowed-entity"
                ))

        # Check required entities
        for req_key in required_entity_keys:
            if req_key not in entities:
                errors.append(ValidationError(
                    filename,
                    f"Missing required entity '{req_key}' for {datatype}/{suffix}",
                    "error",
                    "missing-required-entity"
                ))

        # Suffix validation is implicit since we matched by suffix

        return errors, warnings

    def _find_matching_file_rule(self, datatype: str, suffix: str) -> dict[str, Any] | None:
        """Find the specific file rule that matches datatype and suffix"""
        try:
            schema = self.schema._raw_schema
            files_raw = schema.get('rules', {}).get('files', {}).get('raw', {})

            for _rule_name, rule_data in files_raw.items():
                if isinstance(rule_data, dict):
                    for _file_type, file_rule in rule_data.items():
                        if isinstance(file_rule, dict):
                            # Check if this rule applies to our datatype and suffix
                            rule_datatypes = file_rule.get('datatypes', [])
                            rule_suffixes = file_rule.get('suffixes', [])

                            if datatype in rule_datatypes and suffix in rule_suffixes:
                                return file_rule

            return None
        except Exception:
            return None

    def _check_entity_order(self, filename: str, entities: dict[str, str]) -> list[ValidationError]:
        """Check if entities are in correct order (warning only)"""
        warnings = []

        # Check entity order using shared ENTITY_ORDER constant
        entity_keys = list(entities.keys())

        # Check if entities follow expected order
        filtered_expected = [e for e in ENTITY_ORDER if e in entity_keys]
        if entity_keys != filtered_expected:
            warnings.append(ValidationError(
                filename,
                f"Entity order may not follow BIDS convention (found: {entity_keys}, expected: {filtered_expected})",
                "warning",
                "entity-order"
            ))

        return warnings

    def _compare_entities(self, filename: str, entities: dict[str, str],
                         expected: dict[str, str]) -> list[ValidationError]:
        """Compare entities with expected values"""
        info = []

        for key, expected_value in expected.items():
            if key in entities:
                if entities[key] != expected_value:
                    info.append(ValidationError(
                        filename,
                        f"Entity '{key}' value '{entities[key]}' differs from expected '{expected_value}'",
                        "info",
                        "entity-mismatch"
                    ))
            else:
                info.append(ValidationError(
                    filename,
                    f"Missing expected entity '{key}' with value '{expected_value}'",
                    "info",
                    "missing-expected-entity"
                ))

        return info

    def check_unexpected_root_directories(self, dataset_path: Path, warnings: list[ValidationError]):
        """Check for unexpected directories at dataset root"""
        allowed_root_items = self._get_allowed_root_items_from_schema()

        for item in dataset_path.iterdir():
            if item.is_dir():
                # Skip subject directories
                if item.name.startswith('sub-'):
                    continue
                # Skip allowed directories
                if item.name in allowed_root_items:
                    continue
                # Otherwise it's unexpected
                warnings.append(ValidationError(
                    str(item),
                    f"Unexpected directory at dataset root: {item.name}",
                    "warning",
                    "unexpected-root-directory"
                ))

    def _get_required_files_from_schema(self) -> list[str]:
        """Extract required files from BIDS schema"""
        try:
            schema = self.schema._raw_schema
            required_files = []

            # Get core files marked as required
            core = schema.get('rules', {}).get('files', {}).get('common', {}).get('core', {})
            for filename, rule in core.items():
                if isinstance(rule, dict) and rule.get('level') == 'required':
                    # Add proper extension for certain files
                    if filename == 'dataset_description':
                        required_files.append('dataset_description.json')
                    else:
                        required_files.append(filename)

            return required_files
        except Exception:
            # Fallback to known required file
            return ["dataset_description.json"]

    def _get_recommended_file_groups_from_schema(self) -> list[tuple]:
        """Extract recommended file groups from BIDS schema"""
        try:
            schema = self.schema._raw_schema
            recommended_groups = []

            # Get core files marked as recommended
            core = schema.get('rules', {}).get('files', {}).get('common', {}).get('core', {})
            for filename, rule in core.items():
                if isinstance(rule, dict) and rule.get('level') == 'recommended':
                    # Group alternatives (README vs README.md, CHANGES vs CHANGES.md)
                    if filename == 'README':
                        recommended_groups.append(('README', 'README.md'))
                    elif filename == 'CHANGES':
                        recommended_groups.append(('CHANGES', 'CHANGES.md'))
                    else:
                        recommended_groups.append((filename,))

            # Get table files marked as optional (treat as recommended for warnings)
            tables = schema.get('rules', {}).get('files', {}).get('common', {}).get('tables', {})
            for filename, rule in tables.items():
                if isinstance(rule, dict) and rule.get('level') == 'optional':
                    if filename == 'participants':
                        recommended_groups.append(('participants.tsv',))

            return recommended_groups
        except Exception:
            # Fallback to known recommended files
            return [("README", "README.md"), ("participants.tsv",), ("CHANGES", "CHANGES.md")]

    def _get_allowed_root_items_from_schema(self) -> set:
        """Extract allowed root items from BIDS schema"""
        try:
            schema = self.schema._raw_schema
            allowed = set()

            # Add all files from core rules
            core = schema.get('rules', {}).get('files', {}).get('common', {}).get('core', {})
            for filename, rule in core.items():
                if isinstance(rule, dict):
                    # Add proper extension for certain files
                    if filename == 'dataset_description':
                        allowed.add('dataset_description.json')
                    else:
                        allowed.add(filename)

                    # Add common extensions for some files
                    if filename == 'README':
                        allowed.add('README.md')
                    elif filename == 'CHANGES':
                        allowed.add('CHANGES.md')

            # Add table files
            tables = schema.get('rules', {}).get('files', {}).get('common', {}).get('tables', {})
            for filename, rule in tables.items():
                if isinstance(rule, dict):
                    allowed.add(f"{filename}.tsv")

            # Add standard BIDS directories (these are implicit in the spec)
            allowed.update([
                'sourcedata', 'derivatives', 'code', 'stimuli', 'phenotype',
                '.git', '.github', '.datalad', '.bidsignore'
            ])

            return allowed
        except Exception:
            # Fallback to known allowed items
            return {
                'sourcedata', 'derivatives', 'code', '.git', '.github',
                '.datalad', '.bidsignore', 'stimuli', 'phenotype',
                'dataset_description.json', 'README', 'README.md',
                'CHANGES', 'CHANGES.md', 'participants.tsv'
            }

    def _check_schema_associations(self, data_file_path: Path, datatype: str) -> list[ValidationError]:
        """Check for required associated files based purely on BIDS schema associations"""
        errors = []

        try:
            # Get file information
            filename = data_file_path.name
            suffix = extract_suffix_from_filename(filename)

            # Get schema associations
            schema = self.schema._raw_schema
            associations = schema.get('meta', {}).get('associations', {})

            # Check each association rule from schema only
            for assoc_name, assoc_rule in associations.items():
                if self._file_matches_association_selectors(
                    data_file_path, datatype, suffix, assoc_rule.get('selectors', [])
                ):
                    target = assoc_rule.get('target', {})
                    target_suffix = target.get('suffix')
                    target_extension = target.get('extension')

                    if target_suffix:
                        # Build expected associated file path
                        expected_assoc_file = self._build_associated_file_path(
                            data_file_path, target_suffix, target_extension
                        )

                        # Check if inheritance applies (look in parent directories)
                        inherit = assoc_rule.get('inherit', False)
                        found = self._find_associated_file(data_file_path, expected_assoc_file, inherit)

                        if not found:
                            errors.append(ValidationError(
                                str(data_file_path),
                                f"Missing required associated file: {expected_assoc_file.name}",
                                "error",
                                f"missing-{assoc_name}"
                            ))

        except Exception:
            # If schema parsing fails, don't add any hardcoded rules
            pass

        return errors

    def _file_matches_association_selectors(self, file_path: Path, datatype: str, suffix: str, selectors: list) -> bool:
        """Check if file matches association selector conditions"""
        # This is a simplified implementation - the real schema uses complex expressions
        # For now, implement common patterns

        for selector in selectors:
            if 'intersects([suffix]' in selector:
                # Extract suffix list from selector like "intersects([suffix], ['eeg', 'ieeg', 'meg'])"
                if 'ieeg' in selector and suffix == 'ieeg':
                    return True
                elif 'eeg' in selector and suffix == 'eeg':
                    return True
                # Add other patterns as needed

        return False

    def _build_associated_file_path(self, data_file_path: Path, target_suffix: str, target_extension: str) -> Path:
        """Build the path for an associated file"""
        filename = data_file_path.stem  # Remove extension

        # Replace the suffix part
        parts = filename.split('_')
        if parts:
            parts[-1] = target_suffix  # Replace last part (original suffix) with target suffix
            new_filename = '_'.join(parts) + target_extension
            return data_file_path.parent / new_filename

        return data_file_path.parent / f"{filename}_{target_suffix}{target_extension}"

    def _find_associated_file(self, data_file_path: Path, expected_file_path: Path, inherit: bool) -> bool:
        """Find associated file using BIDS inheritance-aware matching"""

        # Check exact path first
        if expected_file_path.exists():
            return True

        if not inherit:
            return False

        # Use inheritance-aware entity matching like the creation logic
        data_entities = parse_entities_from_filename(data_file_path)

        # Extract target suffix and extension from expected file
        target_filename = expected_file_path.name
        target_parts = target_filename.split('_')
        target_suffix_with_ext = target_parts[-1]  # e.g., "electrodes.tsv"
        target_suffix = target_suffix_with_ext.split('.')[0]  # e.g., "electrodes"
        target_extension = '.' + '.'.join(target_suffix_with_ext.split('.')[1:])  # e.g., ".tsv"

        # Get datatype from path
        datatype = data_file_path.parent.name

        # Get inheritance-aware entity combination using existing method
        inherited_entities = self.schema_helper._get_inheritance_aware_entities(
            data_entities, datatype, target_suffix
        )

        # Build the expected filename using existing method
        candidate_filename = self.schema_helper._build_bids_filename(
            inherited_entities, target_suffix, target_extension
        )
        candidate_path = data_file_path.parent / candidate_filename

        if candidate_path.exists():
            return True

        return False
