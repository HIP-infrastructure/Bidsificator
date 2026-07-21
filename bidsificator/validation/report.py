"""Validation result types: `ValidationError` and `ValidationResult`.

Pure data + presentation, with no dependency on the schema or filesystem. The
UI (`ValidationResultsDialog`) and callers consume `ValidationResult` directly,
so both dataclasses are re-exported from
`bidsificator.services.ValidationServiceSchema` for backward compatibility.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    errors: list[ValidationError] = None
    warnings: list[ValidationError] = None
    info: list[ValidationError] = None

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

    def get_grouped_warnings(self) -> dict[str, dict[str, Any]]:
        """Group warnings by rule type with file lists, matching official validator format"""
        return self._group_issues_by_rule(self.warnings)

    def get_grouped_errors(self) -> dict[str, dict[str, Any]]:
        """Group errors by rule type with file lists"""
        return self._group_issues_by_rule(self.errors)

    def _group_issues_by_rule(self, issues: list[ValidationError]) -> dict[str, dict[str, Any]]:
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
