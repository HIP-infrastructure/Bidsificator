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


class ValidationService:
    """Schema-driven BIDS validation service with comprehensive reporting"""
    
    def __init__(self, schema_manager: Optional[BidsSchemaManager] = None):
        """Initialize with optional schema manager"""
        self.schema = schema_manager or BidsSchemaManager.get_instance()
    
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
        
        # Check required files
        required_files = ["dataset_description.json"]
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
                    desc_errors = self._validate_dataset_description(file_path)
                    errors.extend(desc_errors)
        
        # Check recommended files
        recommended_files = ["README", "README.md", "participants.tsv", "CHANGES", "CHANGES.md"]
        missing_recommended = []
        for rec_file in recommended_files:
            if not (dataset_path / rec_file).exists():
                missing_recommended.append(rec_file)
        
        if len(missing_recommended) == len(recommended_files):
            warnings.append(ValidationError(
                str(dataset_path),
                f"Missing all recommended files: {', '.join(recommended_files)}",
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
    
    def _validate_dataset_description(self, desc_path: Path) -> List[ValidationError]:
        """Validate dataset_description.json content"""
        errors = []
        
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
                sidecar_errors = self._validate_json_sidecar(json_sidecar, datatype)
                errors.extend(sidecar_errors)
        
        return errors, warnings, info
    
    def _validate_json_sidecar(self, json_path: Path, datatype: str) -> List[ValidationError]:
        """Validate JSON sidecar content against schema requirements"""
        errors = []
        
        try:
            with open(json_path, 'r') as f:
                metadata = json.load(f)
            
            dt = self.schema.get_datatype(datatype)
            if dt:
                required_metadata = dt.metadata_requirements.get('required', {})
                
                # Check for required fields
                for field_name in required_metadata:
                    if field_name not in metadata:
                        errors.append(ValidationError(
                            str(json_path),
                            f"Missing required metadata field: {field_name}",
                            "error",
                            "missing-metadata-field"
                        ))
                    elif str(metadata[field_name]).lower() in ['n/a', 'unknown', '']:
                        # Only warn about placeholder values for critical fields
                        if field_name in ['SamplingFrequency', 'TaskName']:
                            errors.append(ValidationError(
                                str(json_path),
                                f"Critical field '{field_name}' has placeholder value: {metadata[field_name]}",
                                "error", 
                                "critical-placeholder-metadata"
                            ))
                        # For other fields, it's acceptable to have placeholder values initially
                        
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
        """Validate filename against datatype-specific rules"""
        errors = []
        warnings = []
        
        dt = self.schema.get_datatype(datatype)
        
        # Create mapping from entity keys to entity names
        key_to_name = {}
        name_to_key = {}
        for entity_key, entity_obj in self.schema.entities.items():
            key_to_name[entity_key] = entity_obj.name.lower().replace(' ', '').replace('-', '')
            name_to_key[entity_obj.name.lower().replace(' ', '').replace('-', '')] = entity_key
        
        # Convert filename entities (keys) to entity names for comparison
        entity_names = []
        for entity_key in entities:
            if entity_key in key_to_name:
                entity_names.append(key_to_name[entity_key])
            else:
                # Fallback: assume key maps to similar name
                if entity_key == 'sub':
                    entity_names.append('subject')
                elif entity_key == 'ses':
                    entity_names.append('session')
                else:
                    entity_names.append(entity_key)
        
        # Check allowed entities (compare entity names)
        for entity_key in entities:
            # Map key to name for comparison
            entity_name = 'subject' if entity_key == 'sub' else (
                'session' if entity_key == 'ses' else entity_key
            )
            if entity_name not in dt.allowed_entities:
                errors.append(ValidationError(
                    filename,
                    f"Entity '{entity_key}' ('{entity_name}') not allowed for datatype '{datatype}'",
                    "error",
                    "disallowed-entity"
                ))
        
        # Check required entities (convert required names to keys)
        required_keys = []
        for req_entity_name in dt.required_entities:
            if req_entity_name == 'subject':
                required_keys.append('sub')
            elif req_entity_name == 'session':
                required_keys.append('ses')
            else:
                # Try to find matching key
                for key, entity_obj in self.schema.entities.items():
                    simplified_name = entity_obj.name.lower().replace(' ', '').replace('-', '')
                    if simplified_name == req_entity_name.lower():
                        required_keys.append(key)
                        break
                else:
                    required_keys.append(req_entity_name)  # Fallback
        
        for req_key in required_keys:
            if req_key not in entities:
                errors.append(ValidationError(
                    filename,
                    f"Missing required entity '{req_key}' for datatype '{datatype}'",
                    "error",
                    "missing-required-entity"
                ))
        
        # Check suffix
        if suffix and suffix not in dt.suffixes:
            errors.append(ValidationError(
                filename,
                f"Invalid suffix '{suffix}' for datatype '{datatype}' (allowed: {', '.join(dt.suffixes)})",
                "error",
                "invalid-suffix"
            ))
        
        return errors, warnings
    
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
        allowed_root_dirs = {
            'sourcedata', 'derivatives', 'code', '.git', '.github', 
            '.datalad', '.bidsignore', 'stimuli', 'phenotype'
        }
        
        for item in dataset_path.iterdir():
            if item.is_dir():
                # Skip subject directories
                if item.name.startswith('sub-'):
                    continue
                # Skip allowed directories
                if item.name in allowed_root_dirs:
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

