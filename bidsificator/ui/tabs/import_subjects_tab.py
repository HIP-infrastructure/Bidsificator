"""Import Subjects tab — a self-contained ``QWidget`` (9d.1).

Owns the lookup table, the subject list + embedded ``FileEditor``, and the batch
import. Built from ``forms/ImportSubjectsTab.ui``. Dependencies are injected by
the host ``MainWindow``: the ``MainController``, the shared ``StatusBarManager``,
and getter/setter callbacks for the shared "last browsed folder" memory. The tab
wires its own ``ImportSubjectsController`` signals and renders its own dialogs
(parented to the tab); status-bar updates go through the injected manager.

The embedded ``FileEditor`` keeps its OWN ``FileEditorController`` (separate from
the one ``MainController`` hands to the ``ImportSubjectsController``); the sync
helpers read that editor-owned controller's ``_current_subject_data``.
"""

import logging
import os
from collections.abc import Callable
from dataclasses import asdict
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QFileDialog, QMenu, QMessageBox, QWidget

from ...core.BidsUtilityFunctions import BidsUtilityFunctions
from ...forms.ImportSubjectsTab_ui import Ui_ImportSubjectsTab
from ..FileEditor import FileEditor

if TYPE_CHECKING:
    from ...controllers.MainController import MainController
    from ..StatusBarManager import StatusBarManager

logger = logging.getLogger(__name__)


class ImportSubjectsTab(QWidget, Ui_ImportSubjectsTab):
    """Import Subjects tab: parse, lookup table, subject list + FileEditor, batch import."""

    def __init__(
        self,
        main_controller: "MainController",
        status_bar: "StatusBarManager",
        get_browse_memory: Callable[[], str],
        set_browse_memory: Callable[[str], None],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        self._main_controller = main_controller
        self._status_bar = status_bar
        self._get_browse_memory = get_browse_memory
        self._set_browse_memory = set_browse_memory
        self._controller = main_controller.import_subjects_controller

        # Embedded FileEditor sits beside the subject list; it owns its own controller.
        self._file_editor = FileEditor()
        self.IS_FileEditorLayout.addWidget(self._file_editor)

        self._connect_ui()
        self._connect_controller()

        # Trigger UI for the first time (third-tab progress bar).
        self.IS_progressBar.setValue(0)

    # --------------------------------------------------------------------- #
    # wiring
    # --------------------------------------------------------------------- #

    def _connect_ui(self):
        """Wire this tab's own widgets (was MainWindow's "Third tab" block)."""
        self.IS_ParsePushButton.clicked.connect(self.parse_subject_to_import)
        self.IS_SubjectListWidget.itemClicked.connect(self.update_import_subject_fileList)
        self.IS_SubjectListWidget.itemSelectionChanged.connect(self.update_import_subject_fileList)
        self.IS_StartImportPushButton.clicked.connect(self.start_subjects_import)
        self.IS_SubjectListWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.IS_SubjectListWidget.customContextMenuRequested.connect(
            self.show_delete_import_subject_context_menu
        )
        self.CreateLutPushButton.clicked.connect(self.create_lookup_template)
        self.BrowseLutPushButton.clicked.connect(self.browse_lookup_table)
        self.lineEdit.textChanged.connect(self.on_lookup_table_path_changed)

    def _connect_controller(self):
        """Wire the ImportSubjectsController's signals (was MainWindow's wiring block)."""
        ctrl = self._controller
        ctrl.subjects_loaded.connect(self._on_subjects_loaded)
        ctrl.selection_changed.connect(self._on_import_subject_selection_changed)
        ctrl.progress_updated.connect(self.IS_progressBar.setValue)
        ctrl.progress_updated.connect(self._on_subjects_import_progress)
        ctrl.import_completed.connect(self._on_subjects_import_completed)
        ctrl.import_failed.connect(self._on_import_failed)
        ctrl.import_failed.connect(self._show_subjects_import_failed_dialog)
        ctrl.operation_failed.connect(self._on_operation_failed)
        ctrl.operation_info.connect(self._on_operation_info)
        ctrl.dialog_dismissed.connect(self._on_dialog_dismissed)
        ctrl.lookup_table_updated.connect(self._on_lookup_table_updated)

    # --------------------------------------------------------------------- #
    # subject list + embedded FileEditor
    # --------------------------------------------------------------------- #

    def _on_subjects_loaded(self):
        """Handle subjects loaded from import subjects controller."""
        self.IS_SubjectListWidget.clear()
        # Use display names to show "OriginalID [MappedID]" format
        display_names = self._controller.get_display_names()
        for display_name in display_names:
            self.IS_SubjectListWidget.addItem(display_name)

        # Auto-select first subject if available, otherwise clear the file editor
        if display_names:
            self.IS_SubjectListWidget.setCurrentRow(0)
            # setCurrentRow doesn't always fire signals; trigger the update manually
            self.update_import_subject_fileList()
        else:
            self._file_editor.clear_file_list()

    def _on_import_subject_selection_changed(self, index: int):
        """Handle import subject selection change from controller."""
        # The controller updates the file editor; nothing to do here.
        pass

    def _on_lookup_table_updated(self, message: str):
        """Handle lookup table update message from controller."""
        logger.debug("Lookup table status: %s", message)

    def parse_subject_to_import(self):
        """Parse subjects for import using the controller."""
        config_path = BidsUtilityFunctions.get_config_path()
        self._main_controller.parse_subjects_to_import(config_path)
        # UI update is handled by the subjects_loaded signal

    def update_import_subject_fileList(self):
        """Update import subject file list using controller data."""
        selectedIndexes = self.IS_SubjectListWidget.selectedIndexes()
        if len(selectedIndexes) > 0:
            selected_row = selectedIndexes[0].row()

            # First, save current FileEditor data back to ImportSubjectsController
            self._sync_file_editor_to_import_controller()

            self._file_editor.clear_file_list()

            # Get subject data from controller using row index
            subject_data = self._controller.model.get_subject(selected_row)
            if subject_data:
                # Convert dataclass to dictionary for FileEditor
                legacy_format = asdict(subject_data)
                self._file_editor.add_files_to_list(legacy_format)

    def _sync_file_editor_to_import_controller(self):
        """Sync FileEditor changes back to ImportSubjectsController."""
        # Save any pending form changes first
        if hasattr(self._file_editor, '_save_form_data'):
            self._file_editor._save_form_data()

        # Get the current subject data from the FileEditor's own controller
        if (hasattr(self._file_editor, '_controller') and
                hasattr(self._file_editor._controller, '_current_subject_data')):

            modified_data = self._file_editor._controller._current_subject_data
            if modified_data and modified_data.get("subject_id"):
                subject_id = modified_data.get("subject_id")
                self._controller.update_subject_data(subject_id, modified_data)

    # --------------------------------------------------------------------- #
    # remove (confirmation lives here in the view)
    # --------------------------------------------------------------------- #

    def show_delete_import_subject_context_menu(self):
        self.customMenu = QMenu(self)
        deleteSelectedSubjectAction = self.customMenu.addAction("Remove Selected Subject(s)")
        deleteSelectedSubjectAction.triggered.connect(self.remove_selected_import_subject)
        selectedIndexes = self.IS_SubjectListWidget.selectedIndexes()
        self.customMenu.setEnabled(len(selectedIndexes) != 0)
        self.customMenu.popup(QCursor.pos())

    def remove_selected_import_subject(self):
        """Remove selected subjects from import list using controller."""
        selectedIndexes = self.IS_SubjectListWidget.selectedIndexes()
        if not selectedIndexes:
            return

        # Confirm here (view) before removing.
        reply = QMessageBox.question(
            self,
            "Remove Subject",
            "Are you sure you want to remove the selected subject(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            return

        indices_to_remove = [index.row() for index in selectedIndexes]
        self._main_controller.remove_selected_import_subjects(indices_to_remove)

    # --------------------------------------------------------------------- #
    # batch import
    # --------------------------------------------------------------------- #

    def start_subjects_import(self):
        """Start subjects import using the controller."""
        # Reset progress bar for this tab
        self.IS_progressBar.setValue(0)

        # Show starting message in status bar
        self._status_bar.show_progress("Batch import in progress...")

        # Save any pending FileEditor changes before import
        self._save_file_editor_changes()

        # Get task value from the FileEditor's TaskComboBox
        task = self._file_editor.TaskComboBox.currentText()

        # The controller calls back into _resolve_subject_conflicts if the dataset
        # already contains some of the subjects being imported.
        self._main_controller.start_subjects_import(task, self._resolve_subject_conflicts)

    def _resolve_subject_conflicts(self, existing_subjects: list[str]) -> str:
        """Ask the user how to handle already-existing subjects.

        Returns "overwrite", "skip", or "cancel" for the controller to act on.
        """
        subject_list = "\n".join([f"• {subject}" for subject in existing_subjects])

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Subject Conflicts Detected")
        if len(existing_subjects) == 1:
            msg.setText(f"The following subject already exists in the dataset:\n\n{subject_list}")
        else:
            msg.setText(
                f"The following {len(existing_subjects)} subjects already exist in the dataset:\n\n"
                f"{subject_list}"
            )
        msg.setInformativeText("How would you like to proceed?")

        overwrite_btn = msg.addButton("Overwrite Existing", QMessageBox.ButtonRole.AcceptRole)
        skip_btn = msg.addButton("Skip These Subjects", QMessageBox.ButtonRole.RejectRole)
        # Cancel is shown but not compared against (anything else is treated as cancel).
        msg.addButton("Cancel Import", QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(skip_btn)
        msg.exec()

        clicked_button = msg.clickedButton()
        if clicked_button == overwrite_btn:
            return "overwrite"
        elif clicked_button == skip_btn:
            return "skip"
        return "cancel"

    def _save_file_editor_changes(self):
        """Save FileEditor changes back to ImportSubjectsController."""
        # Force save of any pending form changes (even if user didn't click "Save")
        if hasattr(self._file_editor, '_save_form_data'):
            self._file_editor._save_form_data()

        # Also update any changed fields from the form directly
        if hasattr(self._file_editor, '_save_form_data_to_controller'):
            self._file_editor._save_form_data_to_controller()

        # Get the modified data from the FileEditor's controller and sync it
        if (hasattr(self._file_editor, '_controller')
                and hasattr(self._file_editor._controller, '_current_subject_data')):
            modified_data = self._file_editor._controller._current_subject_data
            if modified_data and modified_data.get("subject_id"):
                subject_id = modified_data.get("subject_id")
                self._controller.update_subject_data(subject_id, modified_data)

    # --------------------------------------------------------------------- #
    # lookup table
    # --------------------------------------------------------------------- #

    def browse_lookup_table(self):
        """Browse for CSV lookup table file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Lookup Table CSV File",
            self._get_browse_memory(),
            "CSV files (*.csv *.txt);;All files (*.*)"
        )

        if file_path:
            self._set_browse_memory(os.path.dirname(file_path))
            self.lineEdit.setText(file_path)
            # The textChanged signal triggers the controller update

    def on_lookup_table_path_changed(self, path: str):
        """Handle lookup table path change."""
        self._controller.set_lookup_table(path.strip())

    def create_lookup_template(self):
        """Create a lookup table template file (view gathers the save path)."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Lookup Table Template",
            "lookup_table.csv",
            "CSV files (*.csv);;All files (*.*)",
        )
        if not file_path:
            return

        success, message = self._controller.save_lookup_template(file_path)
        if success:
            QMessageBox.information(self, "Template Created", message)
        else:
            QMessageBox.warning(self, "Template Creation Failed", message)

    # --------------------------------------------------------------------- #
    # controller-signal slots (dialogs parented to this tab; status via manager)
    # --------------------------------------------------------------------- #

    def _on_subjects_import_progress(self, progress: int):
        """Handle subjects import progress update for the status bar."""
        self._status_bar.show_progress("Importing subjects...", progress)

    def _on_subjects_import_completed(self, results: dict):
        """Handle subjects import completion: status bar + completion dialog."""
        subject_count = results.get("subjects_imported", 0)
        file_count = results.get("total_files", 0)
        self._status_bar.show_success(
            f"Successfully imported {subject_count} subjects ({file_count} files)"
        )
        QMessageBox.information(
            self,
            "Import Complete",
            f"Successfully imported {subject_count} subjects with {file_count} files.\n\n"
            "Check the dataset folder for the imported files.",
        )

    def _show_subjects_import_failed_dialog(self, message: str):
        """Render a subjects-import failure as a modal."""
        QMessageBox.critical(
            self,
            "Import Failed",
            f"The subject import did not complete:\n\n{message}",
        )

    def _on_import_failed(self, error_message: str):
        """Handle import failure for the status bar."""
        self._status_bar.show_error(f"Import failed: {error_message}")

    def _on_operation_failed(self, title: str, message: str):
        """Render a controller-reported failure (warning)."""
        QMessageBox.warning(self, title, message)

    def _on_operation_info(self, title: str, message: str):
        """Render a controller-reported informational message."""
        QMessageBox.information(self, title, message)

    def _on_dialog_dismissed(self):
        """Handle dialog dismissal - clear the status bar."""
        self._status_bar.clear()
