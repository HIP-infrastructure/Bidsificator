"""Import Files tab — a self-contained ``QWidget`` (9d.2).

Owns the per-file metadata form, the import file list, modality/session/task
handling, the subject dropdown, the contact-labeling file, and the file import.
Built from ``forms/ImportFilesTab.ui``. Dependencies are injected by the host
``MainWindow``: the ``MainController``, the shared ``StatusBarManager``, and
getter/setter callbacks for the shared "last browsed folder" memory. The tab
wires its own ``ImportFilesController`` signals and renders its own dialogs
(parented to the tab); status-bar updates go through the injected manager.

The file list, current subject, and contact-labeling file live in the
``ImportFilesController`` / ``ImportSessionModel`` (single source of truth); this
tab reads/writes them and holds no parallel copy.

Cross-tab: ``refresh_subject_dropdown()`` (formerly ``update_subject_names_dropDown``)
is called by the host when the dataset's subject list changes.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget

from ...forms.ImportFilesTab_ui import Ui_ImportFilesTab
from ..import_completion import (
    CompletionState,
    ImportCompletionDialog,
    select_completion_state,
)

if TYPE_CHECKING:
    from ...controllers.MainController import MainController
    from ..StatusBarManager import StatusBarManager

logger = logging.getLogger(__name__)


class ImportFilesTab(QWidget, Ui_ImportFilesTab):
    """Import Files tab: metadata form, file list, subject/modality/session, import."""

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
        # Cache the controller BEFORE setup_import_files_tab(): its
        # set_import_form_enabled() reads _import_files_controller.file_count.
        self._import_files_controller = main_controller.import_files_controller
        self._reverting_subject = False

        # Set up the tab. populate_modality_dropdown runs BEFORE the
        # ModalityComboBox.currentIndexChanged wiring so filling it does not
        # fire update_modality_UI mid-population (matches the old ordering).
        self.setup_import_files_tab()
        self.populate_modality_dropdown()
        self._setup_session_combobox()

        self._connect_ui()
        self._connect_controller()

        # Trigger UI for the first time (second-tab progress bar + modality UI).
        self.progressBar.setValue(0)
        self.update_modality_UI()

    # --------------------------------------------------------------------- #
    # wiring
    # --------------------------------------------------------------------- #

    def _connect_ui(self):
        """Wire this tab's own widgets (was MainWindow's "Second tab" block)."""
        self.ModalityComboBox.currentIndexChanged.connect(self.update_modality_UI)
        # Browse button removed from UI - files selected via "+" button only
        self.BrowseLineEdit.setReadOnly(True)
        self.TaskComboBox.currentTextChanged.connect(self.update_task_combobox_UI)
        self.AddFileButton.clicked.connect(self.add_multiple_files)
        self.RemoveFileButton.clicked.connect(self.remove_file_from_list)
        self.ImportFileListWidget.itemClicked.connect(self.on_import_file_selected)
        self.ImportFileListWidget.itemSelectionChanged.connect(self.on_import_file_selected)
        self.ClinicalElecPushButton.clicked.connect(self.browse_clinical_electrode_file)
        self.ClinicalElecLineEdit.setReadOnly(True)  # Make read-only like BrowseLineEdit
        self.StartImportPushButton.clicked.connect(self.start_file_import)
        # NOTE: SubjectComboBox.currentTextChanged is intentionally NOT connected
        # here. The update_subject_details / on_subject_changed connections are
        # established lazily at the end of refresh_subject_dropdown (with
        # disconnect guards), so programmatic repopulation does not fire the
        # subject-change dialog.

    def _connect_controller(self):
        """Wire the ImportFilesController's signals (was MainWindow's wiring block)."""
        ctrl = self._import_files_controller
        ctrl.file_list_changed.connect(self.refresh_import_file_list)
        ctrl.form_data_updated.connect(self._update_form_from_data)
        ctrl.progress_updated.connect(self.progressBar.setValue)
        ctrl.progress_updated.connect(self._on_file_import_progress)
        ctrl.import_completed.connect(self._on_file_import_completed)
        ctrl.import_failed.connect(self._on_import_failed)
        ctrl.import_failed.connect(self._show_file_import_failed_dialog)
        ctrl.operation_failed.connect(self._on_operation_failed)
        ctrl.dialog_dismissed.connect(self._on_dialog_dismissed)

    # --------------------------------------------------------------------- #
    # setup
    # --------------------------------------------------------------------- #

    def setup_import_files_tab(self):
        """Initialize the Import Files tab"""
        self.ImportFileListWidget.setSelectionMode(self.ImportFileListWidget.SelectionMode.SingleSelection)
        # Initially disable form elements since no files are loaded
        self.set_import_form_enabled(False)

    def _setup_session_combobox(self):
        """
        Configure SessionComboBox for flexible session input.

        Makes the combobox editable to allow custom session names per BIDS spec.
        Provides default options with ses-post first (selected by default).
        """
        self.SessionComboBox.addItems(['ses-post', 'ses-pre'])
        self.SessionComboBox.setCurrentIndex(0)
        self.SessionComboBox.setEditable(True)
        self.SessionComboBox.setPlaceholderText("Type session name (e.g., baseline, month6, 01)")

    def populate_modality_dropdown(self):
        """Populate ModalityComboBox with available datatypes from schema"""
        try:
            from ...core.bids_constants import MODALITY_DISPLAY_MAPPING
            from ...services.FileDetectionServiceSchema import FileDetectionService

            # Clear existing items (both static ones from UI and any previous dynamic ones)
            self.ModalityComboBox.clear()

            detection_service = FileDetectionService()
            available_datatypes = detection_service.get_all_datatypes()

            for datatype in sorted(available_datatypes):
                if datatype in MODALITY_DISPLAY_MAPPING:
                    for display_name, _suffix in MODALITY_DISPLAY_MAPPING[datatype]:
                        self.ModalityComboBox.addItem(display_name)

        except Exception:
            logger.warning("Could not populate modality dropdown from schema", exc_info=True)
            fallback_items = [
                "T1w (anat)",
                "T2w (anat)",
                "ieeg (ieeg)",
                "eeg (eeg)",
                "photo (ieeg)"
            ]
            for item in fallback_items:
                self.ModalityComboBox.addItem(item)

    # --------------------------------------------------------------------- #
    # form load / save
    # --------------------------------------------------------------------- #

    def _set_session_combobox_text(self, text):
        """Display `text` in the editable SessionComboBox, even when it is not an item.

        Custom session names (typed by the user) are not always in the item list,
        and an empty text must clear the selection so session-less files
        round-trip unchanged through save_current_form_to_data().
        """
        index = self.SessionComboBox.findText(text)
        self.SessionComboBox.setCurrentIndex(index)
        if index < 0:
            self.SessionComboBox.setEditText(text)
        self.SessionComboBox.clearFocus()

    def save_current_form_to_data(self):
        """Save current form fields to the currently selected file in the model."""
        form_data = {
            "modality": self.ModalityComboBox.currentText(),
            "session": self.SessionComboBox.currentText(),
            "task": self.TaskComboBox.currentText(),
            "contrast_agent": self.ContrastAgentLineEdit.text(),
            "acquisition": self.AcquisitionLineEdit.text(),
            "reconstruction": self.ReconstructionLineEdit.text(),
        }
        # No-op when there is no selection; strips the "ses-" prefix internally.
        self._import_files_controller.update_selected_file_from_form(form_data)

    def _load_import_file_into_form(self, index: int):
        """Load a file's metadata into the import form without saving first.

        Used for programmatic selection (refresh/rebuild) where the form may still
        show values from a previously selected file. Saving first would corrupt
        acquisitions (e.g. write acq-02 onto files[0]).
        """
        model = self._import_files_controller.model
        if model.file_model.get_file(index) is None:
            model.selected_file_index = -1
            self.set_import_form_enabled(False)
            self.clear_import_form_fields()
            return

        # Set the model selection directly (the model setter emits no signal) so the
        # form save/load timing stays under the view's control, then populate.
        model.selected_file_index = index
        self._update_form_from_data(model.get_form_data_for_selected_file())

    def on_import_file_selected(self):
        """Update form fields when a file is selected in the list (user-driven)."""
        # Save current form data before switching — only safe for user selection
        # when the form matches the model's current selection.
        self.save_current_form_to_data()

        model = self._import_files_controller.model

        # Use current row if no selection (e.g., when called manually)
        selected_items = self.ImportFileListWidget.selectedItems()
        if not selected_items:
            current_row = self.ImportFileListWidget.currentRow()
            if 0 <= current_row < self._import_files_controller.file_count:
                index = current_row
            else:
                model.selected_file_index = -1
                # No file selected - disable form and clear fields only if no files exist
                if self._import_files_controller.file_count == 0:
                    self.set_import_form_enabled(False)
                    self.clear_import_form_fields()
                return
        else:
            index = self.ImportFileListWidget.row(selected_items[0])

        self._load_import_file_into_form(index)

    def remove_file_from_list(self):
        """Remove the selected file from the import list via the controller."""
        selected_items = self.ImportFileListWidget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a file to remove")
            return

        index = self.ImportFileListWidget.row(selected_items[0])
        # Point the model at the clicked row, then let the controller remove it. The
        # controller re-indexes the selection and emits file_list_changed, which
        # refresh_import_file_list turns into the rebuilt widget + reloaded form.
        self._import_files_controller.model.selected_file_index = index
        self._import_files_controller.remove_selected_file()

    def clear_import_form_fields(self):
        """Clear all import form fields"""
        self.BrowseLineEdit.setText("No file selected")
        self.ContrastAgentLineEdit.clear()
        self.AcquisitionLineEdit.clear()
        self.ReconstructionLineEdit.clear()

    def set_import_form_enabled(self, enabled):
        """Enable or disable import form elements"""
        self.ModalityComboBox.setEnabled(enabled)
        self.TaskComboBox.setEnabled(enabled)
        self.SessionComboBox.setEnabled(enabled)
        self.ContrastAgentLineEdit.setEnabled(enabled)
        self.AcquisitionLineEdit.setEnabled(enabled)
        self.ReconstructionLineEdit.setEnabled(enabled)

        # Remove/Import buttons only make sense when files are present. Guard the
        # controller lookup: this runs during setup_import_files_tab(), which is
        # called after the controller is cached but keep the guard for safety.
        has_files = (hasattr(self, "_import_files_controller")
                     and self._import_files_controller.file_count > 0)
        self.RemoveFileButton.setEnabled(enabled and has_files)
        self.StartImportPushButton.setEnabled(enabled and has_files)

    # --------------------------------------------------------------------- #
    # subject dropdown (cross-tab entry point: refresh_subject_dropdown)
    # --------------------------------------------------------------------- #

    def on_subject_changed(self):
        """Handle subject selection change in Import Files tab."""
        # Prevent recursive calls when reverting the combobox after a cancel
        if getattr(self, "_reverting_subject", False):
            return

        current_subject = self.SubjectComboBox.currentText()
        previous_subject = self._import_files_controller.current_subject

        # Confirm here (view) before re-tagging queued files. The controller tells
        # us when a prompt is warranted (files present and the subject changes).
        if self._import_files_controller.needs_subject_change_confirmation(current_subject):
            reply = QMessageBox.question(
                self,
                "Subject Changed",
                f"You're switching from '{previous_subject}' to '{current_subject}'.\n\n"
                f"What would you like to do with the {self._import_files_controller.file_count} files in the list?\n\n"
                f"• YES: Update all files to use '{current_subject}'\n"
                f"• NO: Cancel - keep '{previous_subject}' selected",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.No:
                self._revert_subject_combobox(previous_subject)
                return

        changed = self._import_files_controller.change_subject(current_subject)
        if changed:
            if previous_subject != current_subject:
                # Subject actually changed: the contact labeling file no longer applies
                self.ClinicalElecLineEdit.clear()
                self._import_files_controller.contact_labeling_file = None
        else:
            # An empty subject is rejected by the model: revert the combobox.
            self._revert_subject_combobox(previous_subject)

    def _revert_subject_combobox(self, previous_subject: str):
        """Restore the subject combobox without re-triggering on_subject_changed."""
        self._reverting_subject = True
        self.set_comboBox_text(self.SubjectComboBox, previous_subject)
        self._reverting_subject = False

    def refresh_subject_dropdown(self):
        """Update subject dropdown using controller data (host calls this on subjects change)."""
        if not self._main_controller.is_dataset_loaded():
            return

        subject_names = self._main_controller.get_current_subjects()

        # Temporarily disconnect signals to prevent unwanted dialogs during update
        try:
            self.SubjectComboBox.currentTextChanged.disconnect(self.update_subject_details)
        except TypeError:
            pass  # Connection doesn't exist
        try:
            self.SubjectComboBox.currentTextChanged.disconnect(self.on_subject_changed)
        except TypeError:
            pass  # Connection doesn't exist

        self.SubjectComboBox.clear()
        self.SubjectComboBox.addItems(subject_names)

        # Sync the controller's current subject to the first available subject (or
        # empty if none), but only when no files are queued, to avoid silently
        # reassigning files the user already added.
        if subject_names and self._import_files_controller.file_count == 0:
            self._import_files_controller.current_subject = subject_names[0]
        elif not subject_names:
            self._import_files_controller.current_subject = ""

        # Reconnect signals after update is complete
        self.SubjectComboBox.currentTextChanged.connect(self.update_subject_details)
        self.SubjectComboBox.currentTextChanged.connect(self.on_subject_changed)

        # Populate session dropdown for the current subject
        if subject_names:
            self.update_subject_details()

    def update_subject_details(self):
        """Update subject details using controller data."""
        subject_name = self.SubjectComboBox.currentText()

        if not subject_name or not self._main_controller.is_dataset_loaded():
            return

        session_names = self._main_controller.get_sessions_for_subject(subject_name)

        # Clear and repopulate, but maintain editable functionality
        displayed_session = self.SessionComboBox.currentText()
        self.SessionComboBox.clear()

        if session_names:
            # Sort sessions to put ses-post first if it exists
            sorted_sessions = sorted(session_names, key=lambda x: (x != 'ses-post', x))
            self.SessionComboBox.addItems(sorted_sessions)
        else:
            self.SessionComboBox.addItems(['ses-post', 'ses-pre'])

        if not self.SessionComboBox.isEditable():
            self.SessionComboBox.setEditable(True)
            self.SessionComboBox.setPlaceholderText("Type session name (e.g., baseline, month6, 01)")

        if self._import_files_controller.file_count > 0:
            # With files pending import, repopulating must not change the
            # displayed session: the next form save would stamp it onto the
            # selected file. This fires between two imports of the same list
            # (worker finished, subject switch), so restore what was shown.
            self._set_session_combobox_text(displayed_session)
        else:
            # No files yet: default to the first entry (ses-post when present).
            self.SessionComboBox.setCurrentIndex(0)

    def update_modality_UI(self):
        if "(anat)" in self.ModalityComboBox.currentText():
            self.SessionLabel.show()
            self.SessionComboBox.show()
            self.TaskLabel.show()
            self.TaskComboBox.show()
            self.ContrastAgentLabel.show()
            self.ContrastAgentLineEdit.show()
            self.AcquisitionLabel.show()
            self.AcquisitionLineEdit.show()
            self.ReconstructionLabel.show()
            self.ReconstructionLineEdit.show()
        elif "ieeg (ieeg)" in self.ModalityComboBox.currentText():
            self.SessionLabel.show()
            self.SessionComboBox.show()
            self.TaskLabel.show()
            self.TaskComboBox.show()
            self.ContrastAgentLabel.hide()
            self.ContrastAgentLineEdit.hide()
            self.AcquisitionLabel.show()
            self.AcquisitionLineEdit.show()
            self.ReconstructionLabel.hide()
            self.ReconstructionLineEdit.hide()
        elif "photo (ieeg)" in self.ModalityComboBox.currentText():
            self.SessionLabel.show()
            self.SessionComboBox.show()
            self.TaskLabel.show()
            self.TaskComboBox.show()
            self.ContrastAgentLabel.hide()
            self.ContrastAgentLineEdit.hide()
            self.AcquisitionLabel.show()
            self.AcquisitionLineEdit.show()
            self.ReconstructionLabel.hide()
            self.ReconstructionLineEdit.hide()
        elif "eeg (eeg)" in self.ModalityComboBox.currentText():
            self.SessionLabel.show()
            self.SessionComboBox.show()
            self.TaskLabel.show()
            self.TaskComboBox.show()
            self.ContrastAgentLabel.hide()
            self.ContrastAgentLineEdit.hide()
            self.AcquisitionLabel.show()
            self.AcquisitionLineEdit.show()
            self.ReconstructionLabel.hide()
            self.ReconstructionLineEdit.hide()
        else:
            logger.warning("[__UpdateModalityUI] Modality not recognized")

    def update_task_combobox_UI(self):
        if "Other" in self.TaskComboBox.currentText():
            task_name = QInputDialog.getText(self, "Enter Task Name", "Enter a name for your task")[0]
            if task_name == "":
                QMessageBox.warning(self, "Dataset Name empty", "Please enter a valid name for your task")
                return
            else:
                self.TaskComboBox.currentTextChanged.disconnect(self.update_task_combobox_UI)
                self.TaskComboBox.insertItem(self.TaskComboBox.count()-1, task_name)
                self.TaskComboBox.setCurrentIndex(self.TaskComboBox.count()-2)
                self.TaskComboBox.currentTextChanged.connect(self.update_task_combobox_UI)

    # --------------------------------------------------------------------- #
    # add / import files
    # --------------------------------------------------------------------- #

    def add_multiple_files(self):
        """Add files to the import list via the controller (single source of truth)."""
        try:
            from ...services.FileDetectionServiceSchema import FileDetectionService

            # Tag new files with the currently selected subject before adding.
            self._import_files_controller.current_subject = self.SubjectComboBox.currentText()

            # Gather the files here (view); the controller runs schema-driven
            # detection, de-duplicates, auto-increments acquisitions, and updates
            # the model. Its file_list_changed signal drives refresh_import_file_list.
            all_filter = FileDetectionService().get_all_supported_extensions()
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select files to import",
                self._get_browse_memory() or "",
                all_filter,
            )
            if not files:
                return
            self._set_browse_memory(str(Path(files[0]).parent))

            count, failed = self._import_files_controller.add_files_from_paths(
                files, self._get_current_form_values()
            )

            # Show the import results summary.
            if count > 0 or failed:
                message = f"Successfully imported {count} files"
                if failed:
                    message += "\n\nFailed files:\n" + "\n".join(failed)
                QMessageBox.information(self, "Import Results", message)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add files: {str(e)}")

    def _get_current_form_values(self):
        """Get current form values for import."""
        return {
            'current_subject': self.SubjectComboBox.currentText(),
            'session': self.SessionComboBox.currentText(),
            'task': self.TaskComboBox.currentText(),
            'contrast_agent': self.ContrastAgentLineEdit.text(),
            'acquisition': self.AcquisitionLineEdit.text(),
            'reconstruction': self.ReconstructionLineEdit.text()
        }

    def refresh_import_file_list(self):
        """Rebuild the ImportFileListWidget from the model without corrupting metadata.

        Must not save the form before loading: after a rebuild the form may still
        show the previously selected file (e.g. acq-02), and writing that back would
        corrupt another file's acquisition. We only read from the model here.
        """
        self.ImportFileListWidget.blockSignals(True)
        try:
            self.ImportFileListWidget.clear()

            names = self._import_files_controller.get_file_names_for_list_widget()
            for display_text in names:
                self.ImportFileListWidget.addItem(display_text)

            if names:
                model = self._import_files_controller.model
                index = model.selected_file_index
                if not 0 <= index < len(names):
                    index = 0
                self.ImportFileListWidget.setCurrentRow(index)
                # Load form from the selected file without saving stale form values first
                self._load_import_file_into_form(index)
            else:
                self._import_files_controller.model.selected_file_index = -1
                self.set_import_form_enabled(False)
                self.clear_import_form_fields()
        finally:
            self.ImportFileListWidget.blockSignals(False)

    def browse_clinical_electrode_file(self):
        """Browse for clinical electrode labeling Excel file."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Excel Files (*.xlsx *.xls)")
        file_dialog.setWindowTitle("Select Contact Labeling File")

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]

                # Validate file using ContactLabelingParser
                try:
                    from ...services.ContactLabelingParser import ContactLabelingParser
                    parser = ContactLabelingParser()
                    contact_data = parser.parse_file(Path(file_path))

                    contact_count = len(contact_data)
                    QMessageBox.information(
                        self,
                        "File Loaded",
                        f"Successfully loaded {contact_count} contacts from labeling file.\n\n"
                        f"File: {Path(file_path).name}"
                    )

                    # Update UI and store on the controller (single source of truth)
                    self.ClinicalElecLineEdit.setText(file_path)
                    self._import_files_controller.contact_labeling_file = file_path

                except FileNotFoundError as e:
                    QMessageBox.warning(
                        self,
                        "File Not Found",
                        f"The selected file could not be found:\n{str(e)}"
                    )
                except ValueError as e:
                    QMessageBox.warning(
                        self,
                        "Invalid File Format",
                        f"Could not parse Excel file:\n{str(e)}\n\n"
                        f"Please ensure the file has the correct structure with a 'contact' column."
                    )
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Error Loading File",
                        f"An unexpected error occurred:\n{str(e)}"
                    )

    def start_file_import(self):
        """Start file import using the controller."""
        # Confirm here (view) before regenerating an existing electrodes.tsv.
        if self._import_files_controller.import_would_regenerate_electrodes():
            subject_name = self._import_files_controller.current_subject
            reply = QMessageBox.question(
                self,
                "Regenerate electrodes.tsv?",
                f"⚠️ The subject '{subject_name}' already has an existing electrodes.tsv file.\n\n"
                f"Importing with a contact labeling file will completely regenerate "
                f"this file with the clinical annotations.\n\n"
                f"⚠️ Warning: Any manual edits to the existing electrodes.tsv will be LOST.\n\n"
                f"Do you want to continue and regenerate?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,  # Default to No for safety
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Save the current form to the selected file before importing
        self.save_current_form_to_data()

        # Reset progress bar for this tab
        self.progressBar.setValue(0)

        # Show starting message in status bar
        self._status_bar.show_progress("File import in progress...")

        # The controller/model already hold the file list, current subject, and
        # contact labeling file (single source of truth) — no view->controller sync.
        self._main_controller.start_file_import()

    def _update_form_from_data(self, form_data: dict):
        """Populate the import form widgets from a model form-data dict.

        Single place that writes the Import Files form. The session value arrives
        with its "ses-" prefix (or empty); _set_session_combobox_text keeps an empty
        session empty so a session-less file round-trips unchanged through
        save_current_form_to_data().
        """
        if not form_data:
            return
        self.set_import_form_enabled(True)
        self.BrowseLineEdit.setText(form_data.get("file_path", "No file selected"))
        self.set_comboBox_text(self.ModalityComboBox, form_data.get("modality", ""))
        self._set_session_combobox_text(form_data.get("session", ""))
        self.set_comboBox_text(self.TaskComboBox, form_data.get("task", ""))
        self.ContrastAgentLineEdit.setText(form_data.get("contrast_agent", ""))
        self.AcquisitionLineEdit.setText(form_data.get("acquisition", ""))
        self.ReconstructionLineEdit.setText(form_data.get("reconstruction", ""))

    def set_comboBox_text(self, comboBox, text):
        index = comboBox.findText(text)
        if index >= 0:
            comboBox.setCurrentIndex(index)
        else:
            comboBox.setCurrentIndex(-1)

        comboBox.clearFocus()

    # --------------------------------------------------------------------- #
    # controller-signal slots (dialogs parented to this tab; status via manager)
    # --------------------------------------------------------------------- #

    def _on_file_import_progress(self, progress: int):
        """Handle file import progress update for the status bar."""
        self._status_bar.show_progress("Importing files...", progress)

    def _on_file_import_completed(self, results: dict):
        """Handle file import completion: status bar + completion dialog.

        Three states (UR-GUI-009): all imported → green success box; some imported
        with failures/skips → amber "completed with errors" dialog listing each
        problem; nothing imported → red. The amber/red status message persists
        after the dialog closes (the controller withholds ``dialog_dismissed``).
        """
        summary = results.get("summary", {})
        file_count = results.get("files_imported", summary.get("imported", 0))
        state = select_completion_state(summary)

        if state is CompletionState.SUCCESS:
            self._status_bar.show_success(f"Successfully imported {file_count} files")
            QMessageBox.information(
                self,
                "Import Complete",
                f"Successfully imported {file_count} files.\n\n"
                "Files remain in the list for review. You can:\n"
                "• Check/modify any file settings\n"
                "• Remove files if needed\n"
                "• Add more files\n"
                "• Re-import if there were issues",
            )
            return

        problems = summary.get("failed", 0) + summary.get("skipped", 0) + len(summary.get("warnings") or [])
        if state is CompletionState.ERROR:
            self._status_bar.show_error(f"No files imported ({problems} problem(s))")
        else:
            self._status_bar.show_warning(f"Import finished with {problems} problem(s)")
        ImportCompletionDialog(self, state, summary, "file").exec()

    def _show_file_import_failed_dialog(self, message: str):
        """Render a file-import failure as a modal."""
        QMessageBox.critical(
            self,
            "Import Failed",
            f"The file import did not complete:\n\n{message}",
        )

    def _on_import_failed(self, error_message: str):
        """Handle import failure for the status bar."""
        self._status_bar.show_error(f"Import failed: {error_message}")

    def _on_operation_failed(self, title: str, message: str):
        """Render a controller-reported failure (warning)."""
        QMessageBox.warning(self, title, message)

    def _on_dialog_dismissed(self):
        """Handle dialog dismissal - clear the status bar."""
        self._status_bar.clear()
