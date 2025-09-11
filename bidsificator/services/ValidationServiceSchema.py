"""
Schema-driven BIDS validation service

Replaces hardcoded validation with dynamic schema-based rules.
Provides comprehensive validation with detailed error reporting.
"""

import json
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from bidsificator.core.schema import BidsSchemaManager
from bidsificator.core.bids_constants import DEFAULT_METADATA_VALUES, ENTITY_ORDER
from bidsificator.core.BidsSubjectSchema import BidsSubject


@dataclass
class ValidationError:
    """Represents a validation error with context"""
    path: str
    message: str
    severity: str = "error"  # "error", "warning", or "info"
    rule: str = "unknown"    # Which rule was violated


@dataclass  
class ValidationResult:
    """Result of validation with detailed error reporting"""
    is_valid: bool
    message: str = ""
    errors: List[ValidationError] = None
    warnings: List[ValidationError] = None
    info: List[ValidationError] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.info is None:
            self.info = []
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        return len(self.warnings)
    
    @property
    def total_issues(self) -> int:
        return len(self.errors) + len(self.warnings)
    
    def get_grouped_warnings(self) -> Dict[str, Dict[str, Any]]:
        """Group warnings by rule type with file lists, matching official validator format"""
        return self._group_issues_by_rule(self.warnings)
    
    def get_grouped_errors(self) -> Dict[str, Dict[str, Any]]:
        """Group errors by rule type with file lists"""
        return self._group_issues_by_rule(self.errors)
    
    def _group_issues_by_rule(self, issues: List[ValidationError]) -> Dict[str, Dict[str, Any]]:
        """Helper method to group issues by rule type with file lists"""
        grouped = {}
        
        for issue in issues:
            rule = issue.rule
            if rule not in grouped:
                grouped[rule] = {
                    'message': issue.message,
                    'severity': issue.severity,
                    'files': []
                }
            
            # Add file path if not already present
            if issue.path not in grouped[rule]['files']:
                grouped[rule]['files'].append(issue.path)
                
        return grouped
    
    def format_official_style(self, dataset_path: str = None) -> str:
        """Format validation results in official BIDS validator style"""
        from pathlib import Path
        
        output_lines = []
        
        # Convert dataset_path for relative path display
        dataset_root = Path(dataset_path) if dataset_path else None
        
        # Format warnings
        grouped_warnings = self.get_grouped_warnings()
        for rule, data in grouped_warnings.items():
            output_lines.append(f"warning: {rule}")
            output_lines.append(data['message'])
            
            # List affected files with relative paths
            for file_path in data['files']:
                if dataset_root and file_path.startswith(str(dataset_root)):
                    # Show relative path from dataset root
                    rel_path = Path(file_path).relative_to(dataset_root)
                    output_lines.append(f"/{rel_path}")
                else:
                    output_lines.append(file_path)
            
            output_lines.append("Search for this issue on Neurostars.")
            output_lines.append("")  # Empty line between warnings
        
        # Format errors
        grouped_errors = self.get_grouped_errors()
        for rule, data in grouped_errors.items():
            output_lines.append(f"error: {rule}")
            output_lines.append(data['message'])
            
            # List affected files with relative paths
            for file_path in data['files']:
                if dataset_root and file_path.startswith(str(dataset_root)):
                    # Show relative path from dataset root
                    rel_path = Path(file_path).relative_to(dataset_root)
                    output_lines.append(f"/{rel_path}")
                else:
                    output_lines.append(file_path)
            
            output_lines.append("Search for this issue on Neurostars.")
            output_lines.append("")  # Empty line between errors
            
        return "\n".join(output_lines).strip()


class ValidationService:
    """Schema-driven BIDS validation service with comprehensive reporting"""
    
    def __init__(self, schema_manager: Optional[BidsSchemaManager] = None):
        """Initialize with optional schema manager"""
        self.schema = schema_manager or BidsSchemaManager.get_instance()
        # Create helper instance for reusing inheritance methods
        self._schema_helper = BidsSubject("01", Path("/tmp"), self.schema)
    
    def validate_dataset(self, dataset_path: str, 
                        subject_filter: Optional[str] = None) -> ValidationResult:
        """
        Validate entire BIDS dataset using schema rules
        
        Args:
            dataset_path: Path to BIDS dataset root
            subject_filter: Optional subject filter (e.g., "sub-01")
            
        Returns:
            ValidationResult with comprehensive error reporting
        """
        dataset_path = Path(dataset_path)
        
        if not dataset_path.exists():
            return ValidationResult(
                is_valid=False,
                message="Dataset path does not exist",
                errors=[ValidationError(str(dataset_path), "Path does not exist", "error", "file-existence")]
            )
        
        errors = []
        warnings = []
        info = []
        
        # Validate root-level files
        root_errors, root_warnings, root_info = self._validate_dataset_root(dataset_path)
        errors.extend(root_errors)
        warnings.extend(root_warnings) 
        info.extend(root_info)
        
        # Validate all subjects (or filtered subject)
        if subject_filter:
            subject_path = dataset_path / subject_filter
            if subject_path.exists():
                subject_result = self.validate_subject(str(dataset_path), subject_filter)
                errors.extend(subject_result.errors)
                warnings.extend(subject_result.warnings)
                info.extend(subject_result.info)
            else:
                errors.append(ValidationError(
                    str(subject_path),
                    f"Subject {subject_filter} does not exist",
                    "error",
                    "subject-existence"
                ))
        else:
            for subject_dir in dataset_path.glob("sub-*"):
                if subject_dir.is_dir():
                    subject_result = self.validate_subject(str(dataset_path), subject_dir.name)
                    errors.extend(subject_result.errors)
                    warnings.extend(subject_result.warnings)
                    info.extend(subject_result.info)
        
        # Check for unexpected directories at root
        self._check_unexpected_root_directories(dataset_path, warnings)
        
        # Generate summary message
        is_valid = len(errors) == 0
        message = self._generate_summary_message(is_valid, len(errors), len(warnings), subject_filter)
        
        return ValidationResult(
            is_valid=is_valid,
            message=message,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def validate_subject(self, dataset_path: str, subject_name: str) -> ValidationResult:
        """
        Validate specific subject using schema rules
        
        Args:
            dataset_path: Path to BIDS dataset root  
            subject_name: Subject name (e.g., "sub-01")
            
        Returns:
            ValidationResult with subject-specific validation
        """
        dataset_path = Path(dataset_path)
        subject_path = dataset_path / subject_name
        
        if not subject_path.exists():
            return ValidationResult(
                is_valid=False,
                message=f"Subject {subject_name} does not exist",
                errors=[ValidationError(str(subject_path), "Subject directory does not exist", "error", "subject-existence")]
            )
        
        errors = []
        warnings = []
        info = []
        
        # Validate subject name format
        subject_id = subject_name.replace("sub-", "") if subject_name.startswith("sub-") else subject_name
        if not self.schema.validate_entity_value("sub", subject_id):
            errors.append(ValidationError(
                str(subject_path),
                f"Invalid subject ID format: {subject_name}",
                "error",
                "subject-format"
            ))
        
        # Validate subject structure
        has_data = self._validate_subject_structure(subject_path, errors, warnings, info)
        
        if not has_data:
            warnings.append(ValidationError(
                str(subject_path),
                "Subject has no data files",
                "warning", 
                "empty-subject"
            ))
        
        is_valid = len(errors) == 0
        message = f"{subject_name} validation: {'✅ Valid' if is_valid else '❌ Invalid'}"
        if warnings:
            message += f" ({len(warnings)} warning(s))"
        
        return ValidationResult(
            is_valid=is_valid,
            message=message,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def validate_filename(self, filename: str, datatype: Optional[str] = None, 
                         expected_entities: Optional[Dict[str, str]] = None) -> ValidationResult:
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
        entities, suffix = self._parse_filename(name)
        
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
    
    def validate_subject_name(self, subject_name: str) -> Tuple[bool, str]:
        """Validate subject name using BIDS schema rules"""
        if not subject_name:
            return False, "Subject name cannot be empty"
        
        subject_id = subject_name.replace("sub-", "") if subject_name.startswith("sub-") else subject_name
        
        if self.schema.validate_entity_value("sub", subject_id):
            return True, ""
        else:
            return False, f"Invalid subject name format: {subject_name}"
    
    
    def validate_session_name(self, session_name: str) -> Tuple[bool, str]:
        """Validate session name using BIDS schema rules"""
        if not session_name:
            return True, ""  # Session is optional
        
        session_id = session_name.replace("ses-", "") if session_name.startswith("ses-") else session_name
        
        if self.schema.validate_entity_value("ses", session_id):
            return True, ""
        else:
            return False, f"Invalid session name format: {session_name}"
    
    def validate_task_name(self, task_name: str) -> Tuple[bool, str]:
        """Validate task name using BIDS schema rules"""
        if not task_name:
            return True, ""  # Task is optional for some datatypes
        
        if self.schema.validate_entity_value("task", task_name):
            return True, ""
        else:
            return False, f"Invalid task name format: {task_name}"
    
    def validate_acquisition_name(self, acquisition_name: str) -> Tuple[bool, str]:
        """Validate acquisition name using BIDS schema rules"""
        if not acquisition_name:
            return True, ""  # Acquisition is optional
        
        if self.schema.validate_entity_value("acq", acquisition_name):
            return True, ""
        else:
            return False, f"Invalid acquisition name format: {acquisition_name}"
    
    def validate_bids_dataset(self, dataset_path: str, 
                            subject_name: Optional[str] = None) -> Tuple[bool, str]:
        """Validate BIDS dataset using schema rules"""
        if subject_name:
            result = self.validate_subject(dataset_path, subject_name)
        else:
            result = self.validate_dataset(dataset_path)
        
        return result.is_valid, result.message
    
    def get_validation_summary(self, dataset_path: str) -> Dict[str, Any]:
        """Get comprehensive validation summary using schema rules"""
        result = self.validate_dataset(dataset_path)
        return {
            'is_valid': result.is_valid,
            'errors': [{'message': e.message, 'path': e.path} for e in result.errors],
            'warnings': [{'message': w.message, 'path': w.path} for w in result.warnings]
        }
    
    # Private helper methods
    def _validate_dataset_root(self, dataset_path: Path) -> Tuple[List[ValidationError], 
                                                                List[ValidationError],
                                                                List[ValidationError]]:
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
                    desc_errors, desc_warnings = self._validate_dataset_description(file_path)
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
                f"Missing all recommended files: README, participants.tsv, CHANGES",
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
    
    def _validate_dataset_description(self, desc_path: Path) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate dataset_description.json content"""
        errors = []
        warnings = []
        
        try:
            with open(desc_path, 'r') as f:
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
                        "The 'Authors' field of 'dataset_description.json' should contain an array of values - with one author per value. This was triggered based on the presence of only one author field. Please ignore if all contributors are already properly listed.",
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
    
    def _validate_participants_tsv(self, tsv_path: Path) -> List[ValidationError]:
        """Validate participants.tsv content"""
        errors = []
        
        try:
            import csv
            with open(tsv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                rows = list(reader)
                
                if 'sex' in reader.fieldnames:
                    for i, row in enumerate(rows, start=2):  # Start at 2 for header row
                        sex_value = row.get('sex', '').strip()
                        if sex_value and sex_value not in ['M', 'F', 'm', 'f', 'male', 'female']:
                            # Check if it's the problematic 'M/F' format
                            if '/' in sex_value:
                                errors.append(ValidationError(
                                    str(tsv_path),
                                    f"A value in a column did not match the acceptable type for that column headers specified format. ('{sex_value}')",
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
    
    def _validate_subject_structure(self, subject_path: Path, errors: List[ValidationError],
                                   warnings: List[ValidationError], info: List[ValidationError]) -> bool:
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
    
    def _validate_datatype_directory(self, datatype_dir: Path, datatype: str) -> Tuple[List[ValidationError],
                                                                                      List[ValidationError], 
                                                                                      List[ValidationError]]:
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
        expected_extensions = self.schema.file_registry.get_supported_extensions(datatype) if hasattr(self.schema, 'file_registry') else []
        
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
                sidecar_results = self._validate_json_sidecar(json_sidecar, datatype)
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
    
    def _validate_json_sidecar(self, json_path: Path, datatype: str) -> List[ValidationError]:
        """Validate JSON sidecar content against context-specific schema requirements"""
        errors = []
        
        try:
            with open(json_path, 'r') as f:
                metadata = json.load(f)
            
            # Get suffix from filename to find context-specific rules
            filename = json_path.stem  # Remove .json extension
            suffix = self._extract_suffix_from_filename(filename)
            
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
                    message = f"A data file's JSON sidecar is missing a key listed as recommended."
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
                                                   metadata: dict, filename: str = None) -> Tuple[List[str], List[str]]:
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
            for sidecar_group_name, sidecar_rules in sidecars.items():
                if isinstance(sidecar_rules, dict):
                    for rule_name, rule_data in sidecar_rules.items():
                        if isinstance(rule_data, dict):
                            selectors = rule_data.get('selectors', [])
                            fields = rule_data.get('fields', {})
                            
                            # Check if this rule applies to our context (include modality)
                            if self._matches_sidecar_selectors(selectors, datatype, suffix, modality, metadata, filename):
                                for field_name, field_rule in fields.items():
                                    level = field_rule if isinstance(field_rule, str) else field_rule.get('level', 'optional')
                                    
                                    if level == 'required':
                                        required_fields.append(field_name)
                                    elif level == 'recommended':
                                        recommended_fields.append(field_name)
            
            return required_fields, recommended_fields
            
        except Exception:
            # Fallback to basic requirements
            return [], []
    
    def _matches_sidecar_selectors(self, selectors: List[str], datatype: str, suffix: str, modality: str = None, metadata: Dict[str, Any] = None, filename: str = None) -> bool:
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
    
    def _evaluate_selector(self, selector: str, datatype: str, suffix: str, modality: str = None, metadata: Dict[str, Any] = None, filename: str = None) -> bool:
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
        import re
        pattern = f'{field}\\s*==\\s*"({re.escape(value)})"'
        return bool(re.search(pattern, selector))
    
    def _evaluate_modality_selector(self, selector: str, datatype: str, modality: str) -> bool:
        """Evaluate modality selector using schema mappings"""
        import re
        match = re.search(r'modality\s*==\s*"([^"]+)"', selector)
        if match:
            expected_modality = match.group(1)
            if expected_modality == modality and self._datatype_belongs_to_modality(datatype, modality):
                return True
        return False
    
    def _evaluate_sidecar_condition(self, selector: str, metadata: Dict[str, Any]) -> bool:
        """Evaluate sidecar property conditions like 'sidecar.LookLocker == true'"""
        import re
        
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
    
    def _evaluate_intersects(self, selector: str, suffix: str, datatype: str, metadata: Dict[str, Any]) -> bool:
        """Evaluate intersects function calls like 'intersects(suffix, ["bold", "sbref"])' """
        import re
        
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
        import re
        
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
    
    def _evaluate_entities_condition(self, selector: str, metadata: Dict[str, Any]) -> bool:
        """Evaluate entities conditions like 'entities.task != null'"""
        import re
        
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
    
    def _evaluate_type_condition(self, selector: str, metadata: Dict[str, Any]) -> bool:
        """Evaluate type function conditions like 'type(sidecar.PartialFourier) != "null"' """
        import re
        
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
    
    def _evaluate_entity_membership(self, selector: str, filename: str, metadata: Dict[str, Any]) -> bool:
        """Evaluate entity membership checks like '"echo" in entities'"""
        import re
        
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
    
    def _parse_filename(self, filename: str) -> Tuple[Dict[str, str], Optional[str]]:
        """Parse BIDS filename into entities and suffix"""
        entities = {}
        suffix = None
        
        # Split on underscores
        parts = filename.split('_')
        
        for i, part in enumerate(parts):
            if '-' in part:
                key, value = part.split('-', 1)
                entities[key] = value
            elif i == len(parts) - 1:
                # Last part without dash is the suffix
                suffix = part
        
        return entities, suffix
    
    def _validate_filename_against_datatype(self, filename: str, entities: Dict[str, str], 
                                           suffix: Optional[str], datatype: str) -> Tuple[List[ValidationError], List[ValidationError]]:
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
    
    def _find_matching_file_rule(self, datatype: str, suffix: str) -> Optional[Dict[str, Any]]:
        """Find the specific file rule that matches datatype and suffix"""
        try:
            schema = self.schema._raw_schema
            files_raw = schema.get('rules', {}).get('files', {}).get('raw', {})
            
            for rule_name, rule_data in files_raw.items():
                if isinstance(rule_data, dict):
                    for file_type, file_rule in rule_data.items():
                        if isinstance(file_rule, dict):
                            # Check if this rule applies to our datatype and suffix
                            rule_datatypes = file_rule.get('datatypes', [])
                            rule_suffixes = file_rule.get('suffixes', [])
                            
                            if datatype in rule_datatypes and suffix in rule_suffixes:
                                return file_rule
            
            return None
        except Exception:
            return None
    
    def _check_entity_order(self, filename: str, entities: Dict[str, str]) -> List[ValidationError]:
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
    
    def _compare_entities(self, filename: str, entities: Dict[str, str], 
                         expected: Dict[str, str]) -> List[ValidationError]:
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
    
    def _check_unexpected_root_directories(self, dataset_path: Path, warnings: List[ValidationError]):
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
    
    def _generate_summary_message(self, is_valid: bool, error_count: int, 
                                 warning_count: int, subject_filter: Optional[str]) -> str:
        """Generate comprehensive summary message"""
        scope = f"Subject {subject_filter}" if subject_filter else "Dataset"
        
        if is_valid:
            message = f"{scope} is BIDS compliant"
            if warning_count > 0:
                message += f" with {warning_count} warning(s)"
        else:
            message = f"{scope} validation failed: {error_count} error(s)"
            if warning_count > 0:
                message += f" and {warning_count} warning(s)"
        
        return message
    
    def _get_required_files_from_schema(self) -> List[str]:
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
    
    def _get_recommended_file_groups_from_schema(self) -> List[tuple]:
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
    
    def _check_schema_associations(self, data_file_path: Path, datatype: str) -> List[ValidationError]:
        """Check for required associated files based purely on BIDS schema associations"""
        errors = []
        
        try:
            # Get file information
            filename = data_file_path.name
            suffix = self._extract_suffix_from_filename(filename)
            
            # Get schema associations
            schema = self.schema._raw_schema
            associations = schema.get('meta', {}).get('associations', {})
            
            # Check each association rule from schema only
            for assoc_name, assoc_rule in associations.items():
                if self._file_matches_association_selectors(data_file_path, datatype, suffix, assoc_rule.get('selectors', [])):
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
    
    def _extract_suffix_from_filename(self, filename: str) -> str:
        """Extract suffix from filename (last part before extension)"""
        name = Path(filename).stem
        parts = name.split('_')
        return parts[-1] if parts else ""
    
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
    
    def _parse_entities_from_filename(self, file_path: Path) -> Dict[str, str]:
        """Parse BIDS entities from filename"""
        filename = file_path.stem  # Remove extension
        entities = {}
        
        parts = filename.split('_')
        for part in parts[:-1]:  # Skip last part (suffix)
            if '-' in part:
                key, value = part.split('-', 1)
                entities[key] = value
                
        return entities
    
    def _find_associated_file(self, data_file_path: Path, expected_file_path: Path, inherit: bool) -> bool:
        """Find associated file using BIDS inheritance-aware matching"""
        
        # Check exact path first
        if expected_file_path.exists():
            return True
        
        if not inherit:
            return False
        
        # Use inheritance-aware entity matching like the creation logic
        data_entities = self._parse_entities_from_filename(data_file_path)
        
        # Extract target suffix and extension from expected file
        target_filename = expected_file_path.name
        target_parts = target_filename.split('_')
        target_suffix_with_ext = target_parts[-1]  # e.g., "electrodes.tsv"
        target_suffix = target_suffix_with_ext.split('.')[0]  # e.g., "electrodes"
        target_extension = '.' + '.'.join(target_suffix_with_ext.split('.')[1:])  # e.g., ".tsv"
        
        # Get datatype from path 
        datatype = data_file_path.parent.name
        
        # Get inheritance-aware entity combination using existing method
        inherited_entities = self._schema_helper._get_inheritance_aware_entities(
            data_entities, datatype, target_suffix
        )
        
        # Build the expected filename using existing method
        candidate_filename = self._schema_helper._build_bids_filename(
            inherited_entities, target_suffix, target_extension
        )
        candidate_path = data_file_path.parent / candidate_filename
        
        if candidate_path.exists():
            return True
        
        return False
    
    def _get_field_description(self, field_name: str) -> Optional[str]:
        """Get field description from schema using existing schema access pattern"""
        try:
            # Use existing schema access pattern from the validation service
            schema = self.schema._raw_schema
            objects = schema.get('objects', {})
            
            # Look through schema objects for field descriptions
            for obj_name, obj_data in objects.items():
                if isinstance(obj_data, dict) and obj_data.get('name') == field_name:
                    return obj_data.get('description', '')
            
            return None
        except Exception:
            return None
    
    def _validate_slicetiming_elements(self, json_path: Path, metadata: Dict[str, Any], errors: List[ValidationError]) -> None:
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
                    f"The number of elements in the 'SliceTiming' array should match the 'k' dimension of the corresponding NIfTI volume.",
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
                        f"The number of elements in the 'SliceTiming' array should match the 'k' dimension of the corresponding NIfTI volume.",
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

