"""
Dialog for displaying detailed BIDS validation results
"""

from PyQt6.QtWidgets import (
    QDialog, QTreeWidgetItem, QProgressDialog,
    QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from ..forms.ValidationResultsDialog_ui import Ui_ValidationResultsDialog


@dataclass
class ValidationItem:
    """Represents a validation issue"""
    path: str
    message: str
    severity: str  # 'error', 'warning', 'info'
    rule: str


class ValidationResultsDialog(QDialog):
    """Dialog to display comprehensive BIDS validation results"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup UI from .ui file
        self.ui = Ui_ValidationResultsDialog()
        self.ui.setupUi(self)
        
        self._setup_connections()
        
    def _setup_connections(self):
        """Setup signal connections"""
        # Connect toggle buttons to filter function
        self.ui.errorButton.clicked.connect(self._filter_display)
        self.ui.warningButton.clicked.connect(self._filter_display)
        self.ui.infoButton.clicked.connect(self._filter_display)
        
        # Connect tree selection to details display
        self.ui.treeWidget.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Connect buttons
        self.ui.exportButton.clicked.connect(self._export_report)
        self.ui.closeButton.clicked.connect(self.accept)
        
        # Set initial column widths
        self.ui.treeWidget.setColumnWidth(0, 100)
        self.ui.treeWidget.setColumnWidth(1, 300)
    
    def display_validation_result(self, validation_result):
        """Display validation results from ValidationService"""
        # Update summary
        if validation_result.is_valid:
            self.ui.summaryLabel.setText("✅ Dataset is BIDS Compliant")
            self.ui.summaryLabel.setStyleSheet("color: green;")
        else:
            self.ui.summaryLabel.setText("❌ Dataset Validation Failed")
            self.ui.summaryLabel.setStyleSheet("color: red;")
        
        # Store validation result for filtering
        self.validation_result = validation_result
        
        # Update button texts
        self.ui.errorButton.setText(f"❌ Errors: {len(validation_result.errors)}")
        self.ui.warningButton.setText(f"⚠️ Warnings: {len(validation_result.warnings)}")
        self.ui.infoButton.setText(f"ℹ️ Info: {len(validation_result.info)}")
        
        # Populate tree with current filters
        self._populate_tree()
    
    def _populate_tree(self):
        """Populate tree widget based on current filter settings"""
        if not hasattr(self, 'validation_result'):
            return
            
        # Clear tree
        self.ui.treeWidget.clear()
        
        # Check which types to show
        show_errors = self.ui.errorButton.isChecked()
        show_warnings = self.ui.warningButton.isChecked()
        show_info = self.ui.infoButton.isChecked()
        
        # Group issues by rule type (official validator style)
        grouped_warnings = self.validation_result.get_grouped_warnings()
        grouped_errors = self.validation_result.get_grouped_errors() if hasattr(self.validation_result, 'get_grouped_errors') else {}
        
        # Process errors first (if enabled)
        if show_errors:
            for rule, error_info in sorted(grouped_errors.items()):
                # Create rule node
                rule_item = QTreeWidgetItem(self.ui.treeWidget)
                rule_item.setText(0, "❌")
                rule_item.setText(1, f"error: {rule}")
                rule_item.setText(2, error_info['message'])
                rule_item.setForeground(1, QColor("red"))
                rule_item.setExpanded(True)
                
                # Add affected files as children
                for file_path in sorted(error_info['files']):
                    file_item = QTreeWidgetItem(rule_item)
                    file_item.setText(1, self._get_relative_path(file_path))
                    file_item.setForeground(1, QColor("red"))
                    # Store original issue data for details
                    if self.validation_result.errors:
                        for error in self.validation_result.errors:
                            if error.path == file_path and error.rule == rule:
                                file_item.setData(0, Qt.ItemDataRole.UserRole, error)
                                break
        
        # Process warnings (if enabled)
        if show_warnings:
            for rule, warning_info in sorted(grouped_warnings.items()):
                # Create rule node
                rule_item = QTreeWidgetItem(self.ui.treeWidget)
                rule_item.setText(0, "⚠️")
                rule_item.setText(1, f"warning: {rule}")
                rule_item.setText(2, warning_info['message'])
                rule_item.setForeground(1, QColor("orange"))
                rule_item.setExpanded(True)
                
                # Add affected files as children
                for file_path in sorted(warning_info['files']):
                    file_item = QTreeWidgetItem(rule_item)
                    file_item.setText(1, self._get_relative_path(file_path))
                    file_item.setForeground(1, QColor("orange"))
                    # Store original issue data for details
                    for warning in self.validation_result.warnings:
                        if warning.path == file_path and warning.rule == rule:
                            file_item.setData(0, Qt.ItemDataRole.UserRole, warning)
                            break
        
        # Process info (if enabled) - similar to warnings but in blue
        if show_info and hasattr(self.validation_result, 'info') and self.validation_result.info:
            for info in self.validation_result.info:
                # For now, treat each info as individual items since we don't have grouped info
                info_item = QTreeWidgetItem(self.ui.treeWidget)
                info_item.setText(0, "ℹ️")
                info_item.setText(1, f"info: {info.rule}")
                info_item.setText(2, info.message)
                info_item.setForeground(1, QColor("blue"))
                info_item.setData(0, Qt.ItemDataRole.UserRole, info)
        
        # Auto-resize columns
        for i in range(3):
            self.ui.treeWidget.resizeColumnToContents(i)
    
    def _filter_display(self):
        """Handle filter button clicks to show/hide issue types"""
        self._populate_tree()
    
    def _get_relative_path(self, path: str) -> str:
        """Get relative path from dataset root for display"""
        import os
        
        # Get relative path components
        path_parts = path.split(os.sep)
        
        # Try to identify subject/session/datatype
        for i, part in enumerate(path_parts):
            if part.startswith("sub-"):
                # Found subject, construct relative path from there
                return os.sep.join(path_parts[i:])
        
        # If no subject found, use filename or last few components
        if len(path_parts) > 2:
            return os.sep.join(path_parts[-2:])
        else:
            return os.path.basename(path)
    
    def _get_location_key(self, path: str) -> str:
        """Extract a meaningful location key from path"""
        import os
        
        # Get relative path components
        path_parts = path.split(os.sep)
        
        # Try to identify subject/session/datatype
        for i, part in enumerate(path_parts):
            if part.startswith("sub-"):
                # Found subject, construct relative path from there
                return os.sep.join(path_parts[i:])
        
        # If no subject found, use last 2-3 components
        if len(path_parts) > 2:
            return os.sep.join(path_parts[-3:])
        else:
            return path
    
    def _on_selection_changed(self):
        """Handle tree selection change"""
        items = self.ui.treeWidget.selectedItems()
        if items:
            item = items[0]
            issue = item.data(0, Qt.ItemDataRole.UserRole)
            if issue:
                details = f"Path: {issue.path}\n"
                details += f"Severity: {issue.severity}\n"
                details += f"Rule: {issue.rule}\n"
                details += f"Message: {issue.message}"
                self.ui.detailsText.setText(details)
            else:
                self.ui.detailsText.clear()
    
    def _export_report(self):
        """Export validation report to file"""
        from PyQt6.QtWidgets import QFileDialog
        import json
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Validation Report",
            "validation_report.json",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*.*)"
        )
        
        if filename:
            try:
                # Collect all issues
                report = {
                    "summary": self.ui.summaryLabel.text(),
                    "errors": [],
                    "warnings": [],
                    "info": []
                }
                
                # Iterate through tree items
                for i in range(self.ui.treeWidget.topLevelItemCount()):
                    location_item = self.ui.treeWidget.topLevelItem(i)
                    for j in range(location_item.childCount()):
                        child = location_item.child(j)
                        issue = child.data(0, Qt.ItemDataRole.UserRole)
                        if issue:
                            issue_dict = {
                                "path": issue.path,
                                "message": issue.message,
                                "rule": issue.rule
                            }
                            if issue.severity == "error":
                                report["errors"].append(issue_dict)
                            elif issue.severity == "warning":
                                report["warnings"].append(issue_dict)
                            else:
                                report["info"].append(issue_dict)
                
                # Write report
                if filename.endswith('.json'):
                    with open(filename, 'w') as f:
                        json.dump(report, f, indent=2)
                else:
                    with open(filename, 'w') as f:
                        f.write(f"{report['summary']}\n\n")
                        f.write(f"Errors ({len(report['errors'])})\n")
                        f.write("=" * 50 + "\n")
                        for error in report["errors"]:
                            f.write(f"- {error['path']}: {error['message']}\n")
                        f.write(f"\nWarnings ({len(report['warnings'])})\n")
                        f.write("=" * 50 + "\n")
                        for warning in report["warnings"]:
                            f.write(f"- {warning['path']}: {warning['message']}\n")
                
                QMessageBox.information(self, "Export Complete", f"Report exported to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export report: {str(e)}")


class ValidationProgressDialog(QProgressDialog):
    """Progress dialog for validation operations"""
    
    def __init__(self, parent=None):
        super().__init__("Validating BIDS dataset...", "Cancel", 0, 0, parent)
        self.setWindowTitle("BIDS Validation")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumDuration(500)
        self.setAutoClose(False)
        self.setAutoReset(False)
        
        # Make it indeterminate progress
        self.setRange(0, 0)
        
    def set_status(self, message: str):
        """Update status message"""
        self.setLabelText(message)
        QApplication.processEvents()