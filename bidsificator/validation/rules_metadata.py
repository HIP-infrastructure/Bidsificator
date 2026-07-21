"""Metadata / JSON-sidecar validation rules.

`MetadataRuleValidator` owns the `dataset_description.json` and data-file JSON
sidecar checks, including the BIDS schema selector-expression evaluation used to
resolve which metadata fields are required/recommended for a given context.
Extracted from the ValidationService god class; it holds only the schema manager.
"""

import json
import re
from pathlib import Path
from typing import Any

from bidsificator.validation._parsing import extract_suffix_from_filename
from bidsificator.validation.report import ValidationError


class MetadataRuleValidator:
    """Schema-driven checks for dataset_description.json and data-file sidecars."""

    def __init__(self, schema):
        self.schema = schema

    def validate_dataset_description(self, desc_path: Path) -> tuple[list[ValidationError], list[ValidationError]]:
        """Validate dataset_description.json content"""
        errors = []
        warnings = []

        try:
            with open(desc_path) as f:
                desc = json.load(f)

            # Check required fields
            required_fields = ["Name", "BIDSVersion"]
            for field in required_fields:
                if field not in desc:
                    errors.append(ValidationError(
                        str(desc_path),
                        f"Missing required field: {field}",
                        "error",
                        "missing-dataset-field"
                    ))

            # Check AUTHORS field format (warn if few/no authors)
            if "Authors" in desc:
                authors = desc["Authors"]
                if isinstance(authors, list) and len(authors) <= 1:
                    warnings.append(ValidationError(
                        str(desc_path),
                        "The 'Authors' field of 'dataset_description.json' should contain an array of values - "
                        "with one author per value. "
                        "This was triggered based on the presence of only one author field. "
                        "Please ignore if all contributors are already properly listed.",
                        "warning",
                        "TOO_FEW_AUTHORS"
                    ))

            # Validate BIDSVersion format
            if "BIDSVersion" in desc:
                bids_version = desc["BIDSVersion"]
                if not re.match(r'^\d+\.\d+\.\d+$', str(bids_version)):
                    errors.append(ValidationError(
                        str(desc_path),
                        f"Invalid BIDSVersion format: {bids_version}",
                        "error",
                        "invalid-bids-version"
                    ))

        except json.JSONDecodeError as e:
            errors.append(ValidationError(
                str(desc_path),
                f"Invalid JSON: {e}",
                "error",
                "invalid-json"
            ))
        except Exception as e:
            errors.append(ValidationError(
                str(desc_path),
                f"Error reading file: {e}",
                "error",
                "file-read-error"
            ))

        return errors, warnings

    def validate_json_sidecar(self, json_path: Path, datatype: str) -> list[ValidationError]:
        """Validate JSON sidecar content against context-specific schema requirements"""
        errors = []

        try:
            with open(json_path) as f:
                metadata = json.load(f)

            # Get suffix from filename to find context-specific rules
            filename = json_path.stem  # Remove .json extension
            suffix = extract_suffix_from_filename(filename)

            # Find matching metadata requirements for this specific context
            json_filename = json_path.stem  # Get filename without .json extension for entity parsing
            required_fields, recommended_fields = self._get_context_specific_metadata_requirements(
                datatype, suffix, metadata, json_filename
            )

            # Check for required fields only - don't treat recommended as required
            for field_name in required_fields:
                if field_name not in metadata:
                    errors.append(ValidationError(
                        str(json_path),
                        f"Missing required metadata field: {field_name}",
                        "error",
                        "missing-metadata-field"
                    ))
                elif str(metadata[field_name]).lower() in ['n/a', 'unknown', '']:
                    # Only error for critical fields with placeholder values
                    if field_name in ['SamplingFrequency', 'TaskName']:
                        errors.append(ValidationError(
                            str(json_path),
                            f"Critical field '{field_name}' has placeholder value: {metadata[field_name]}",
                            "error",
                            "critical-placeholder-metadata"
                        ))

            # Check for recommended fields - create warnings for missing ones
            for field_name in recommended_fields:
                if field_name not in metadata:
                    # Get field description from schema if available
                    field_desc = self._get_field_description(field_name)
                    message = "A data file's JSON sidecar is missing a key listed as recommended."
                    if field_desc:
                        message += f" (Field description: {field_desc})"

                    errors.append(ValidationError(
                        str(json_path),
                        message,
                        "warning",
                        f"SIDECAR_KEY_RECOMMENDED ({field_name})"
                    ))

            # Check SliceTiming array length vs NIfTI k-dimension
            if 'SliceTiming' in metadata:
                self._validate_slicetiming_elements(json_path, metadata, errors)

        except json.JSONDecodeError as e:
            errors.append(ValidationError(
                str(json_path),
                f"Invalid JSON in sidecar: {e}",
                "error",
                "invalid-sidecar-json"
            ))
        except Exception as e:
            errors.append(ValidationError(
                str(json_path),
                f"Error reading sidecar: {e}",
                "error",
                "sidecar-read-error"
            ))

        return errors

    def _get_context_specific_metadata_requirements(self, datatype: str, suffix: str,
                                                   metadata: dict, filename: str = None) -> tuple[list[str], list[str]]:
        """Get metadata requirements for specific datatype/suffix context"""
        try:
            schema = self.schema._raw_schema
            sidecars = schema.get('rules', {}).get('sidecars', {})

            required_fields = []
            recommended_fields = []

            # Get modality mappings from schema
            modality_mappings = self.schema._parser._extract_modality_mappings(schema)

            # Find which modality this datatype belongs to
            modality = None
            for mod, datatypes in modality_mappings.items():
                if datatype in datatypes:
                    modality = mod
                    break

            # Look through sidecar rules for matching selectors
            for _sidecar_group_name, sidecar_rules in sidecars.items():
                if isinstance(sidecar_rules, dict):
                    for _rule_name, rule_data in sidecar_rules.items():
                        if isinstance(rule_data, dict):
                            selectors = rule_data.get('selectors', [])
                            fields = rule_data.get('fields', {})

                            # Check if this rule applies to our context (include modality)
                            if self._matches_sidecar_selectors(
                                selectors, datatype, suffix, modality, metadata, filename
                            ):
                                for field_name, field_rule in fields.items():
                                    level = (
                                        field_rule if isinstance(field_rule, str)
                                        else field_rule.get('level', 'optional')
                                    )

                                    if level == 'required':
                                        required_fields.append(field_name)
                                    elif level == 'recommended':
                                        recommended_fields.append(field_name)

            return required_fields, recommended_fields

        except Exception:
            # Fallback to basic requirements
            return [], []

    def _matches_sidecar_selectors(
        self, selectors: list[str], datatype: str, suffix: str, modality: str = None,
        metadata: dict[str, Any] = None, filename: str = None
    ) -> bool:
        """Check if sidecar rule selectors match current context using proper BIDS schema expression evaluation"""
        if not selectors:
            return True

        # CRITICAL: All selectors must match (AND logic) - this is BIDS schema behavior
        for selector in selectors:
            try:
                if not self._evaluate_selector(selector, datatype, suffix, modality, metadata or {}, filename):
                    return False
            except Exception:
                # Conservative fallback - if evaluation fails, assume no match
                return False
        return True

    def _evaluate_selector(
        self, selector: str, datatype: str, suffix: str, modality: str = None,
        metadata: dict[str, Any] = None, filename: str = None
    ) -> bool:
        """Evaluate a single BIDS schema selector expression"""
        selector = selector.strip()

        # Handle exact datatype equality
        if self._contains_exact_match(selector, 'datatype', datatype):
            return True
        elif 'datatype ==' in selector and not self._contains_exact_match(selector, 'datatype', datatype):
            return False

        # Handle exact suffix equality
        if self._contains_exact_match(selector, 'suffix', suffix):
            return True
        elif 'suffix ==' in selector and not self._contains_exact_match(selector, 'suffix', suffix):
            return False

        # Handle modality equality with schema mapping
        if 'modality ==' in selector:
            return self._evaluate_modality_selector(selector, datatype, modality)

        # Handle sidecar property conditions
        if 'sidecar.' in selector:
            return self._evaluate_sidecar_condition(selector, metadata)

        # Handle intersects function calls
        if 'intersects(' in selector:
            return self._evaluate_intersects(selector, suffix, datatype, metadata)

        # Handle match function calls (regex)
        if 'match(' in selector:
            return self._evaluate_match(selector)

        # Handle entities conditions
        if 'entities.' in selector:
            return self._evaluate_entities_condition(selector, metadata)

        # Handle type function calls
        if 'type(' in selector:
            return self._evaluate_type_condition(selector, metadata)

        # Handle entity membership checks like '"echo" in entities'
        if ' in entities' in selector:
            return self._evaluate_entity_membership(selector, filename or suffix, metadata)

        # If no specific condition found, assume it matches (backward compatibility)
        return True

    def _contains_exact_match(self, selector: str, field: str, value: str) -> bool:
        """Check if selector contains exact field == "value" match"""
        pattern = f'{field}\\s*==\\s*"({re.escape(value)})"'
        return bool(re.search(pattern, selector))

    def _evaluate_modality_selector(self, selector: str, datatype: str, modality: str) -> bool:
        """Evaluate modality selector using schema mappings"""
        match = re.search(r'modality\s*==\s*"([^"]+)"', selector)
        if match:
            expected_modality = match.group(1)
            if expected_modality == modality and self._datatype_belongs_to_modality(datatype, modality):
                return True
        return False

    def _evaluate_sidecar_condition(self, selector: str, metadata: dict[str, Any]) -> bool:
        """Evaluate sidecar property conditions like 'sidecar.LookLocker == true'"""
        # Handle boolean equality: sidecar.property == true/false
        match = re.search(r'sidecar\.([^\s=]+)\s*==\s*(true|false)', selector)
        if match:
            property_name = match.group(1)
            expected_value = match.group(2) == 'true'
            actual_value = metadata.get(property_name, False)
            return bool(actual_value) == expected_value

        # Handle boolean inequality: sidecar.property != true/false
        match = re.search(r'sidecar\.([^\s=!]+)\s*!=\s*(true|false)', selector)
        if match:
            property_name = match.group(1)
            expected_value = match.group(2) == 'true'
            actual_value = metadata.get(property_name, False)
            return bool(actual_value) != expected_value

        # Handle string equality: sidecar.property == "value"
        match = re.search(r'sidecar\.([^\s=]+)\s*==\s*"([^"]+)"', selector)
        if match:
            property_name = match.group(1)
            expected_value = match.group(2)
            return metadata.get(property_name) == expected_value

        return False

    def _evaluate_intersects(self, selector: str, suffix: str, datatype: str, metadata: dict[str, Any]) -> bool:
        """Evaluate intersects function calls like 'intersects(suffix, ["bold", "sbref"])' """
        # Handle intersects(suffix, [array])
        match = re.search(r'intersects\(suffix,\s*\[([^\]]+)\]\)', selector)
        if match:
            values_str = match.group(1)
            values = re.findall(r'"([^"]+)"', values_str)
            return suffix in values

        # Handle intersects([suffix], [array]) - alternative format
        match = re.search(r'intersects\(\[suffix\],\s*\[([^\]]+)\]\)', selector)
        if match:
            values_str = match.group(1)
            values = re.findall(r'"([^"]+)"', values_str)
            return suffix in values

        # Handle intersects(dataset.datatypes, [array])
        match = re.search(r'intersects\(dataset\.datatypes,\s*\[([^\]]+)\]\)', selector)
        if match:
            # For now, assume we don't have multi-modal datasets
            return False

        return False

    def _evaluate_match(self, selector: str) -> bool:
        """Evaluate match function for regex patterns"""
        # Handle match(extension, "pattern") - assume .nii/.nii.gz files
        match = re.search(r'match\(extension,\s*["\']([^"\']+)["\']\)', selector)
        if match:
            pattern = match.group(1)
            # Test against common BIDS extensions
            test_extensions = ['.nii', '.nii.gz']
            for ext in test_extensions:
                if re.match(pattern, ext):
                    return True
            return False

        return True

    def _evaluate_entities_condition(self, selector: str, metadata: dict[str, Any]) -> bool:
        """Evaluate entities conditions like 'entities.task != null'"""
        # Handle entities.property != null
        match = re.search(r'entities\.([^\s=!]+)\s*!=\s*null', selector)
        if match:
            entity_name = match.group(1)
            # Check if entity exists based on metadata or common patterns
            if entity_name == 'task':
                return 'TaskName' in metadata and metadata['TaskName'] is not None
            elif entity_name == 'chunk':
                return 'chunk' in metadata  # Rarely present
            return False

        # Handle entities.property == null
        match = re.search(r'entities\.([^\s=]+)\s*==\s*null', selector)
        if match:
            entity_name = match.group(1)
            if entity_name == 'task':
                return 'TaskName' not in metadata or metadata['TaskName'] is None
            return True  # Most entities are null by default

        return False

    def _evaluate_type_condition(self, selector: str, metadata: dict[str, Any]) -> bool:
        """Evaluate type function conditions like 'type(sidecar.PartialFourier) != "null"' """
        # Handle type(sidecar.property) != "null"
        match = re.search(r'type\(sidecar\.([^)]+)\)\s*!=\s*"null"', selector)
        if match:
            property_name = match.group(1)
            return property_name in metadata and metadata[property_name] is not None

        # Handle type(sidecar.property) == "string"
        match = re.search(r'type\(sidecar\.([^)]+)\)\s*==\s*"string"', selector)
        if match:
            property_name = match.group(1)
            value = metadata.get(property_name)
            return isinstance(value, str) and value != ""

        return False

    def _evaluate_entity_membership(self, selector: str, filename: str, metadata: dict[str, Any]) -> bool:
        """Evaluate entity membership checks like '"echo" in entities'"""
        # Extract the entity name from selector like '"echo" in entities'
        match = re.search(r'"([^"]+)"\s+in\s+entities', selector)
        if match:
            entity_name = match.group(1)

            # Parse entities from the actual filename
            if filename:
                parts = filename.split('_')
                filename_entities = {}
                for part in parts[:-1]:  # Skip last part (suffix)
                    if '-' in part:
                        key, value = part.split('-', 1)
                        filename_entities[key] = value

                # Check if the specific entity is present in the filename
                is_present = entity_name in filename_entities

                # Special case for task - also check metadata
                if entity_name == 'task' and not is_present:
                    is_present = 'TaskName' in metadata and metadata['TaskName'] is not None

                return is_present

            return False

        return False

    def _datatype_belongs_to_modality(self, datatype: str, modality: str) -> bool:
        """Check if datatype belongs to modality using schema's modality mappings"""
        try:
            # Use the schema's modality mappings from the parser
            modality_mappings = self.schema._parser._extract_modality_mappings(self.schema._raw_schema)

            # Check if this modality maps to the datatype
            if modality in modality_mappings:
                return datatype in modality_mappings[modality]

            return False
        except Exception:
            # Fallback - if we can't access schema mappings
            return False

    def _get_field_description(self, field_name: str) -> str | None:
        """Get field description from schema using existing schema access pattern"""
        try:
            # Use existing schema access pattern from the validation service
            schema = self.schema._raw_schema
            objects = schema.get('objects', {})

            # Look through schema objects for field descriptions
            for _obj_name, obj_data in objects.items():
                if isinstance(obj_data, dict) and obj_data.get('name') == field_name:
                    return obj_data.get('description', '')

            return None
        except Exception:
            return None

    def _validate_slicetiming_elements(
        self, json_path: Path, metadata: dict[str, Any], errors: list[ValidationError]
    ) -> None:
        """Validate SliceTiming array length matches NIfTI k-dimension"""
        try:
            slice_timing = metadata.get('SliceTiming', [])

            # Handle string values like "n/a" - these should be arrays for proper validation
            if isinstance(slice_timing, str):
                # Find corresponding NIfTI file to report the error against
                nii_path = json_path.with_suffix('.nii.gz')
                if not nii_path.exists():
                    nii_path = json_path.with_suffix('.nii')
                    if not nii_path.exists():
                        return  # No NIfTI file to check against

                # The official validator expects SliceTiming to be an array, not a string
                errors.append(ValidationError(
                    str(nii_path),  # Report on the .nii file
                    "The number of elements in the 'SliceTiming' array should match the 'k' dimension of "
                    "the corresponding NIfTI volume.",
                    "warning",
                    "SLICETIMING_ELEMENTS"
                ))
                return

            if not isinstance(slice_timing, list):
                return

            # Find corresponding NIfTI file
            nii_path = json_path.with_suffix('.nii.gz')
            if not nii_path.exists():
                nii_path = json_path.with_suffix('.nii')
                if not nii_path.exists():
                    return  # No NIfTI file to check against

            # Try to get k-dimension using nibabel if available
            try:
                import nibabel as nib
                nii_img = nib.load(str(nii_path))
                k_dimension = nii_img.shape[2] if len(nii_img.shape) >= 3 else 1

                if len(slice_timing) != k_dimension:
                    errors.append(ValidationError(
                        str(nii_path),  # Report on the .nii file, not .json
                        "The number of elements in the 'SliceTiming' array should match the 'k' dimension of "
                        "the corresponding NIfTI volume.",
                        "warning",
                        "SLICETIMING_ELEMENTS"
                    ))

            except ImportError:
                # nibabel not available - skip this validation
                pass
            except Exception:
                # Error reading NIfTI file - skip this validation
                pass

        except Exception:
            # Error in SliceTiming validation - skip
            pass
