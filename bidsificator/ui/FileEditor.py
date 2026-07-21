import logging

from PyQt6.QtWidgets import QInputDialog, QMessageBox, QWidget

from ..controllers.FileEditorController import FileEditorController
from ..forms.FileEditor_ui import Ui_FileEditor

logger = logging.getLogger(__name__)


class FileEditor(QWidget, Ui_FileEditor):
    """Pure view component for file editing using FileEditorController."""

    def __init__(self):
        super(QWidget, self).__init__()
        self.setupUi(self)

        # Initialize controller
        self._controller = FileEditorController(self)
        self._setup_controller_connections()
        self._setup_ui_connections()

        # Populate modality dropdown with schema-driven values
        self.populate_modality_dropdown()

        # Make SessionComboBox editable for custom session names
        self._setup_session_combobox()

        # Set default selections for comboboxes
        self._set_default_combobox_selections()

    def _set_default_combobox_selections(self):
        """Set default selections for comboboxes during initialization."""
        # TaskComboBox should default to first item
        if self.TaskComboBox.count() > 0:
            self.TaskComboBox.setCurrentIndex(0)

    def _setup_session_combobox(self):
        """
        Configure SessionComboBox for flexible session input.

        Makes the combobox editable to allow custom session names per BIDS spec.
        Keeps only ses-pre and ses-post from UI, users can type any other session name.
        """
        # Make combobox editable to allow custom session names
        self.SessionComboBox.setEditable(True)

        # Keep existing items (ses-pre, ses-post) from UI form
        # Users can type any other session name (baseline, followup, month6, etc.)

        # Set placeholder text to guide users
        self.SessionComboBox.setPlaceholderText("Type session name (e.g., baseline, month6, 01)")

    def _setup_controller_connections(self):
        """Set up connections between controller and UI."""
        self._controller.file_list_updated.connect(self._update_file_list_display)
        self._controller.file_selected.connect(self._update_form_fields)
        self._controller.edit_mode_changed.connect(self._update_edit_mode_ui)
        self._controller.task_list_updated.connect(self._update_task_list)
        self._controller.operation_failed.connect(self._on_operation_failed)

    def _setup_ui_connections(self):
        """Set up UI signal connections."""
        # File list interactions
        self.FileListWidget.itemClicked.connect(self._on_file_list_clicked)
        self.FileListWidget.itemSelectionChanged.connect(self._on_file_list_selection_changed)

        # Edit mode buttons
        self.EditPushButton.clicked.connect(self._on_edit_button_clicked)
        self.CancelPushButton.clicked.connect(self._on_cancel_button_clicked)

        # Form field changes
        self.ModalityComboBox.currentIndexChanged.connect(self.update_userinterface_for_modality)
        self.ModalityComboBox.currentTextChanged.connect(self._on_field_changed)
        self.SessionComboBox.currentTextChanged.connect(self._on_field_changed)
        self.TaskComboBox.currentTextChanged.connect(self.update_task_combobox_UI)
        self.TaskComboBox.currentTextChanged.connect(self._on_field_changed)
        self.ContrastAgentLineEdit.textEdited.connect(self._on_field_changed)
        self.ContrastAgentLineEdit.editingFinished.connect(self._on_field_finished)
        self.AcquisitionLineEdit.textEdited.connect(self._on_field_changed)
        self.AcquisitionLineEdit.editingFinished.connect(self._on_field_finished)
        self.ReconstructionLineEdit.textEdited.connect(self._on_field_changed)
        self.ReconstructionLineEdit.editingFinished.connect(self._on_field_finished)
        self.PathLineEdit.textEdited.connect(self._on_field_changed)
        self.PathLineEdit.editingFinished.connect(self._on_field_finished)

    # Public interface methods (for backward compatibility)

    def add_files_to_list(self, subject):
        """Add files to list using controller."""
        self._controller.add_files_to_list(subject)

    def append_to_list(self, subject):
        """Append subject to list using controller."""
        try:
            error_message = self._controller.append_to_list(subject)
            if error_message:
                raise Exception(error_message)
        except Exception as e:
            raise e

    def remove_selected_file_from_list(self):
        """Remove selected file using controller."""
        self._controller.remove_selected_file()

    def clear_file_list(self):
        """Clear file list using controller."""
        self._controller.clear_file_list()

    def add_file_to_list(self, file_name):
        """Add single file name to UI list widget."""
        self.FileListWidget.addItem(file_name)

    # UI Event Handlers

    def _on_file_list_clicked(self):
        """Handle file list click."""
        self._select_current_file()

    def _on_file_list_selection_changed(self):
        """Handle file list selection change."""
        self._select_current_file()

    def _select_current_file(self):
        """Select current file in controller."""
        # Only persist form edits when in edit mode. Saving while browsing would
        # write stale Acquisition/Task values onto the previously selected file
        # (and onto files[0] during programmatic list rebuilds).
        if self._controller.edit_mode:
            self._save_form_data()

        current_row = self.FileListWidget.currentRow()
        if current_row >= 0:
            self._controller.select_file(current_row)

    def _save_form_data(self):
        """Save current form data to controller."""
        form_data = {
            "modality": self.ModalityComboBox.currentText(),
            "session": self.SessionComboBox.currentText(),
            "task": self.TaskComboBox.currentText(),
            "contrast_agent": self.ContrastAgentLineEdit.text(),
            "acquisition": self.AcquisitionLineEdit.text(),
            "reconstruction": self.ReconstructionLineEdit.text()
        }
        self._controller.save_current_form_data(form_data)

    def _on_edit_button_clicked(self):
        """Handle edit button click."""
        self._controller.toggle_edit_mode()

    def _on_cancel_button_clicked(self):
        """Handle cancel button click."""
        self._controller.cancel_edit_changes()

    def _on_field_changed(self):
        """Handle form field change."""
        if self._controller.edit_mode:
            self._save_form_data_to_controller()

    def _on_field_finished(self):
        """Handle form field finished editing."""
        if self._controller.edit_mode:
            self._save_form_data_to_controller()

    def _save_form_data_to_controller(self):
        """Save current form data to controller."""
        field_data = {
            "modality": self.ModalityComboBox.currentText(),
            "session": self.SessionComboBox.currentText(),
            "task": self.TaskComboBox.currentText(),
            "contrast_agent": self.ContrastAgentLineEdit.text(),
            "acquisition": self.AcquisitionLineEdit.text(),
            "reconstruction": self.ReconstructionLineEdit.text(),
            "file_path": self.PathLineEdit.text()
        }
        self._controller.update_selected_file(field_data)

    # Controller Signal Handlers

    def _update_file_list_display(self):
        """Update file list display from controller."""
        # Block signals so setCurrentRow does not trigger _select_current_file
        # (which could save stale form data). Controller selects the file explicitly.
        self.FileListWidget.blockSignals(True)
        try:
            self.FileListWidget.clear()
            file_names = self._controller.get_file_names_for_list()
            for file_name in file_names:
                self.FileListWidget.addItem(file_name)

            # Auto-select first file if available, otherwise clear form
            if file_names:
                self.FileListWidget.setCurrentRow(0)
            else:
                # No files - clear the form fields
                self._clear_form_fields()
        finally:
            self.FileListWidget.blockSignals(False)

    def _update_form_fields(self, file_data):
        """Update form fields from controller data."""
        modality = file_data.get("modality", "")

        self.set_comboBox_text(self.ModalityComboBox, modality)

        session = file_data.get("session", "")
        session_text = f"ses-{session}" if session else ""
        self.set_comboBox_text(self.SessionComboBox, session_text)

        self.set_comboBox_text(self.TaskComboBox, file_data.get("task", ""))
        self.ContrastAgentLineEdit.setText(file_data.get("contrast_agent", ""))
        self.AcquisitionLineEdit.setText(file_data.get("acquisition", ""))
        self.ReconstructionLineEdit.setText(file_data.get("reconstruction", ""))
        self.PathLineEdit.setText(file_data.get("file_path", ""))

        # Update UI visibility based on modality
        self.update_userinterface_for_modality()

    def _clear_form_fields(self):
        """Clear all form fields when no files are present."""
        self.set_comboBox_text(self.ModalityComboBox, "")
        self.set_comboBox_text(self.SessionComboBox, "")
        self.set_comboBox_text(self.TaskComboBox, "")
        self.ContrastAgentLineEdit.clear()
        self.AcquisitionLineEdit.clear()
        self.ReconstructionLineEdit.clear()
        self.PathLineEdit.clear()

    def _update_edit_mode_ui(self, edit_mode):
        """Update UI for edit mode."""
        # Update button text and visibility
        if edit_mode:
            self.EditPushButton.setText("Save")
            self.CancelPushButton.setEnabled(True)
        else:
            self.EditPushButton.setText("Edit")
            self.CancelPushButton.setEnabled(False)

        self.FileListWidget.setEnabled(not edit_mode)

        # Enable/disable form fields based on edit mode
        self.ModalityComboBox.setEnabled(edit_mode)
        self.SessionComboBox.setEnabled(edit_mode)
        self.TaskComboBox.setEnabled(edit_mode)
        self.ContrastAgentLineEdit.setEnabled(edit_mode)
        self.AcquisitionLineEdit.setEnabled(edit_mode)
        self.ReconstructionLineEdit.setEnabled(edit_mode)
        self.PathLineEdit.setEnabled(edit_mode)

    def populate_modality_dropdown(self):
        """Populate ModalityComboBox with available datatypes from schema"""
        try:
            from ..core.bids_constants import MODALITY_DISPLAY_MAPPING
            from ..services.FileDetectionServiceSchema import FileDetectionService

            # Clear existing items (both static ones from UI and any previous dynamic ones)
            self.ModalityComboBox.clear()

            # Get available datatypes from schema
            detection_service = FileDetectionService()
            available_datatypes = detection_service.get_all_datatypes()

            # Add items for available datatypes using the shared display labels.
            for datatype in sorted(available_datatypes):
                if datatype in MODALITY_DISPLAY_MAPPING:
                    for display_name, _suffix in MODALITY_DISPLAY_MAPPING[datatype]:
                        self.ModalityComboBox.addItem(display_name)

        except Exception:
            logger.warning("Could not populate modality dropdown from schema", exc_info=True)
            # Fallback to basic items if schema loading fails
            fallback_items = [
                "T1w (anat)",
                "T2w (anat)",
                "ieeg (ieeg)",
                "eeg (eeg)",
                "photo (ieeg)"
            ]
            for item in fallback_items:
                self.ModalityComboBox.addItem(item)

    def _update_task_list(self, tasks):
        """Update task list from controller."""
        current_text = self.TaskComboBox.currentText()
        self.TaskComboBox.currentTextChanged.disconnect(self.update_task_combobox_UI)
        self.TaskComboBox.currentTextChanged.disconnect(self._on_field_changed)

        self.TaskComboBox.clear()
        self.TaskComboBox.addItems(tasks)

        # Restore selection if possible, otherwise select first item
        if current_text:
            index = self.TaskComboBox.findText(current_text)
            if index >= 0:
                self.TaskComboBox.setCurrentIndex(index)
            elif self.TaskComboBox.count() > 0:
                # If previous selection not found, select first item
                self.TaskComboBox.setCurrentIndex(0)
        elif self.TaskComboBox.count() > 0:
            # No previous selection, select first item
            self.TaskComboBox.setCurrentIndex(0)

        self.TaskComboBox.currentTextChanged.connect(self.update_task_combobox_UI)
        self.TaskComboBox.currentTextChanged.connect(self._on_field_changed)

    # UI Utility Methods

    def update_task_combobox_UI(self):
        """Handle task combobox selection, prompting for a name on "Other"."""
        current_text = self.TaskComboBox.currentText()
        if "Other" in current_text:
            # Get current tasks
            current_tasks = [self.TaskComboBox.itemText(i) for i in range(self.TaskComboBox.count())]

            # Gather the custom task name here (view), then let the controller
            # validate/insert it. Rejections come back via operation_failed.
            new_task, _ok = QInputDialog.getText(
                self,
                "Enter Task Name",
                "Enter a name for your task",
            )
            self._controller.add_custom_task(new_task, current_tasks)
            # A successful add updates the combobox via the task_list_updated signal.

    def _on_operation_failed(self, title: str, message: str):
        """Render a controller-reported failure as a warning dialog."""
        QMessageBox.warning(self, title, message)

    def update_userinterface_for_modality(self):
        """Update UI visibility based on modality using controller."""
        modality = self.ModalityComboBox.currentText()

        if not modality:
            return

        # Extract datatype from modality string (e.g., "ieeg (ieeg)" -> "ieeg")
        if '(' in modality and ')' in modality:
            # Extract the datatype from parentheses
            datatype = modality.split('(')[1].rstrip(')')
        else:
            datatype = modality

        # Get UI requirements from controller
        requirements = self._controller.get_modality_ui_requirements(datatype)

        # Update visibility based on requirements
        self.SessionLabel.setVisible(requirements.get('show_session', False))
        self.SessionComboBox.setVisible(requirements.get('show_session', False))
        self.TaskLabel.setVisible(requirements.get('show_task', False))
        self.TaskComboBox.setVisible(requirements.get('show_task', False))
        self.ContrastAgentLabel.setVisible(requirements.get('show_contrast', False))
        self.ContrastAgentLineEdit.setVisible(requirements.get('show_contrast', False))
        self.AcquisitionLabel.setVisible(requirements.get('show_acquisition', False))
        self.AcquisitionLineEdit.setVisible(requirements.get('show_acquisition', False))
        self.ReconstructionLabel.setVisible(requirements.get('show_reconstruction', False))
        self.ReconstructionLineEdit.setVisible(requirements.get('show_reconstruction', False))

    def set_comboBox_text(self, comboBox, text):
        """Set combobox text and clear focus."""
        index = comboBox.findText(text)
        if index >= 0:
            comboBox.setCurrentIndex(index)
        else:
            # If text not found or empty, use appropriate default
            default_index = self._get_default_combobox_index(comboBox)
            comboBox.setCurrentIndex(default_index)
        comboBox.clearFocus()

    def _get_default_combobox_index(self, comboBox):
        """Get default index for combobox when text is not found."""
        # TaskComboBox should default to first item when empty
        if comboBox is self.TaskComboBox and comboBox.count() > 0:
            return 0
        # Other comboboxes default to no selection
        return -1

