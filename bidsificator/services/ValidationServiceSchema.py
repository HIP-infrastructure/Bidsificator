"""
Schema-driven BIDS validation service

Replaces hardcoded validation with dynamic schema-based rules.
Provides comprehensive validation with detailed error reporting.

This module is the public entry point. The rule implementations live in the
``bidsificator.validation`` package (`report`, `rules_files`, `rules_metadata`);
`ValidationService` is a thin facade that orchestrates them. `ValidationError`
and `ValidationResult` are re-exported here so existing imports keep working.
"""

from pathlib import Path
from typing import Any

from bidsificator.core.BidsSubjectSchema import BidsSubject
from bidsificator.core.schema import BidsSchemaManager
from bidsificator.validation.report import ValidationError, ValidationResult
from bidsificator.validation.rules_files import FileRuleValidator
from bidsificator.validation.rules_metadata import MetadataRuleValidator

__all__ = ["ValidationService", "ValidationError", "ValidationResult"]


class ValidationService:
    """Schema-driven BIDS validation service with comprehensive reporting"""

    def __init__(self, schema_manager: BidsSchemaManager | None = None):
        """Initialize with optional schema manager"""
        self.schema = schema_manager or BidsSchemaManager.get_instance()
        # Create helper instance for reusing inheritance methods
        self._schema_helper = BidsSubject("01", Path("/tmp"), self.schema)
        # Rule collaborators; file checks descend into metadata checks, so the
        # metadata validator is injected into the file validator.
        self._metadata_rules = MetadataRuleValidator(self.schema)
        self._file_rules = FileRuleValidator(self.schema, self._schema_helper, self._metadata_rules)

    def validate_dataset(self, dataset_path: str,
                        subject_filter: str | None = None) -> ValidationResult:
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
        root_errors, root_warnings, root_info = self._file_rules.validate_dataset_root(dataset_path)
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
        self._file_rules.check_unexpected_root_directories(dataset_path, warnings)

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
                errors=[ValidationError(
                    str(subject_path), "Subject directory does not exist", "error", "subject-existence"
                )]
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
        has_data = self._file_rules.validate_subject_structure(subject_path, errors, warnings, info)

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
        return self._file_rules.validate_filename(filename, datatype, expected_entities)

    def validate_subject_name(self, subject_name: str) -> tuple[bool, str]:
        """Validate subject name using BIDS schema rules"""
        if not subject_name:
            return False, "Subject name cannot be empty"

        subject_id = subject_name.replace("sub-", "") if subject_name.startswith("sub-") else subject_name

        if self.schema.validate_entity_value("sub", subject_id):
            return True, ""
        else:
            return False, f"Invalid subject name format: {subject_name}"


    def validate_session_name(self, session_name: str) -> tuple[bool, str]:
        """Validate session name using BIDS schema rules"""
        if not session_name:
            return True, ""  # Session is optional

        session_id = session_name.replace("ses-", "") if session_name.startswith("ses-") else session_name

        if self.schema.validate_entity_value("ses", session_id):
            return True, ""
        else:
            return False, f"Invalid session name format: {session_name}"

    def validate_task_name(self, task_name: str) -> tuple[bool, str]:
        """Validate task name using BIDS schema rules"""
        if not task_name:
            return True, ""  # Task is optional for some datatypes

        if self.schema.validate_entity_value("task", task_name):
            return True, ""
        else:
            return False, f"Invalid task name format: {task_name}"

    def validate_acquisition_name(self, acquisition_name: str) -> tuple[bool, str]:
        """Validate acquisition name using BIDS schema rules"""
        if not acquisition_name:
            return True, ""  # Acquisition is optional

        if self.schema.validate_entity_value("acq", acquisition_name):
            return True, ""
        else:
            return False, f"Invalid acquisition name format: {acquisition_name}"

    def validate_bids_dataset(self, dataset_path: str,
                            subject_name: str | None = None) -> tuple[bool, str]:
        """Validate BIDS dataset using schema rules"""
        if subject_name:
            result = self.validate_subject(dataset_path, subject_name)
        else:
            result = self.validate_dataset(dataset_path)

        return result.is_valid, result.message

    def get_validation_summary(self, dataset_path: str) -> dict[str, Any]:
        """Get comprehensive validation summary using schema rules"""
        result = self.validate_dataset(dataset_path)
        return {
            'is_valid': result.is_valid,
            'errors': [{'message': e.message, 'path': e.path} for e in result.errors],
            'warnings': [{'message': w.message, 'path': w.path} for w in result.warnings]
        }

    def _generate_summary_message(self, is_valid: bool, error_count: int,
                                 warning_count: int, subject_filter: str | None) -> str:
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
