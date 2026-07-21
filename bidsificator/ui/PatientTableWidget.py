from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QInputDialog,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)

from ..controllers.PatientTableController import PatientTableController


class PatientTableWidget(QTableWidget):
    """Pure view component for patient/subject table using PatientTableController."""

    subject_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize without controller (will be set later)
        self._controller = None
        self._dataset_path_provider = None

        self._setup_ui_connections()

        # UI state
        self._selected_item = None
        self._previous_cell_text = None

    def initialize_controller(self, dataset_path_provider):
        """Initialize the controller after construction (for UI file compatibility)."""
        if self._controller is None:
            self._dataset_path_provider = dataset_path_provider
            self._controller = PatientTableController(dataset_path_provider, self)
            self._setup_controller_connections()

    def _setup_controller_connections(self):
        """Set up connections between controller and UI."""
        self._controller.subjects_loaded.connect(self._on_subjects_loaded)
        self._controller.subject_created.connect(self._on_subject_created)
        self._controller.subject_updated.connect(self._on_subject_updated)
        self._controller.subject_deleted.connect(self._on_subject_deleted)
        self._controller.keys_updated.connect(self._on_keys_updated)
        self._controller.data_changed.connect(self._on_data_changed)
        self._controller.operation_failed.connect(self._on_operation_failed)

    def _setup_ui_connections(self):
        """Set up UI signal connections."""
        self.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self._show_horizontal_context_menu)
        self.verticalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.verticalHeader().customContextMenuRequested.connect(self._show_vertical_context_menu)

    def _connect_table_widget(self):
        """Connect table widget signals."""
        self.itemClicked.connect(self._on_item_clicked)
        self.itemChanged.connect(self._on_item_changed)

    def _disconnect_table_widget(self):
        """Disconnect table widget signals."""
        try:
            self.itemClicked.disconnect(self._on_item_clicked)
        except TypeError:
            pass
        try:
            self.itemChanged.disconnect(self._on_item_changed)
        except TypeError:
            pass

    def _show_horizontal_context_menu(self, position):
        """Show horizontal header context menu."""
        index = self.indexAt(position)
        if not index.isValid():
            return

        self._selected_item = self.indexAt(position)
        can_add_key_before = self._selected_item.column() > 0

        context_menu = QMenu(self)
        add_key_after_action = context_menu.addAction("Add key after Selected")
        add_key_after_action.triggered.connect(self._add_key_after_selected)
        add_key_before_action = context_menu.addAction("Add key before Selected")
        add_key_before_action.setEnabled(can_add_key_before)
        add_key_before_action.triggered.connect(self._add_key_before_selected)
        remove_key_action = context_menu.addAction("Remove Selected key")
        remove_key_action.triggered.connect(self._remove_selected_key)

        context_menu.popup(QCursor.pos())

    def _show_vertical_context_menu(self, position):
        """Show vertical header context menu."""
        index = self.indexAt(position)
        if not index.isValid():
            return

        self._selected_item = self.indexAt(position)

        context_menu = QMenu(self)
        delete_subject_action = context_menu.addAction("Remove Selected Subject")
        delete_subject_action.triggered.connect(self._delete_selected_subject)

        context_menu.popup(QCursor.pos())

    # Public interface methods (for backward compatibility)

    def GetSubjectsKeysFromTable(self):
        """Get subjects keys from table (legacy method)."""
        if self._controller:
            return self._controller.get_subjects_keys_from_data()
        return {}

    def LoadSubjectsInTableWidget(self, dataset_path: str):
        """Load subjects into table widget using controller."""
        if self._controller:
            self._controller.load_subjects(dataset_path)

    def CreateSubjectInTableWidget(self, subject_name: str):
        """Create subject in table widget using controller."""
        if self._controller:
            self._controller.create_subject(subject_name)

    # UI Event Handlers

    def _prompt_new_key_name(self):
        """Ask the user for a new key name; returns the text (empty if cancelled)."""
        key_name, ok = QInputDialog.getText(self, "Add Key", "Enter name for the new key:")
        return key_name if ok else ""

    def _add_key_before_selected(self):
        """Add key before selected column using controller."""
        if self._selected_item and self._controller:
            self._controller.add_key_before(self._selected_item.column(), self._prompt_new_key_name())

    def _add_key_after_selected(self):
        """Add key after selected column using controller."""
        if self._selected_item and self._controller:
            self._controller.add_key_after(self._selected_item.column(), self._prompt_new_key_name())

    def _remove_selected_key(self):
        """Remove selected key using controller, confirming first."""
        if self._selected_item and self._controller:
            column_to_delete = self._selected_item.column()
            key_to_delete = self.horizontalHeaderItem(column_to_delete).text()
            # Confirm removal for real keys; the controller guards (and reports)
            # the reserved subject_id column without a confirmation prompt.
            if key_to_delete != "subject_id":
                reply = QMessageBox.question(
                    self,
                    "Remove Key",
                    f"Are you sure you want to remove the '{key_to_delete}' key?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            self._controller.remove_key(key_to_delete)

    def _on_operation_failed(self, title: str, message: str):
        """Render a controller-reported failure as a warning dialog."""
        QMessageBox.warning(self, title, message)

    def _delete_selected_subject(self):
        """Delete selected subject using controller."""
        if self._selected_item and self._controller:
            row_to_delete = self._selected_item.row()
            subject_id = self.item(row_to_delete, 0).text()
            self._controller.delete_subject(subject_id)

    def _on_item_changed(self, item):
        """Handle item change using controller."""
        if not self._controller:
            return

        if item.column() == 0:
            # Subject ID change
            old_subject_id = self._previous_cell_text
            new_subject_id = item.text()
            self._controller.update_subject_field(old_subject_id, "subject_id", new_subject_id)
        else:
            # Optional key change
            subject_id = self.item(item.row(), 0).text()
            field_name = self.horizontalHeaderItem(item.column()).text()
            new_value = item.text()
            self._controller.update_subject_field(subject_id, field_name, new_value)

    def _on_item_clicked(self, item):
        """Handle item click."""
        self._previous_cell_text = item.text()

    # Controller Signal Handlers

    def _on_subjects_loaded(self):
        """Handle subjects loaded from controller."""
        self._update_table_display()

    def _on_subject_created(self, subject_id: str):
        """Handle subject created from controller."""
        self._update_table_display()
        self.subject_updated.emit()

    def _on_subject_updated(self, subject_id: str):
        """Handle subject updated from controller."""
        self.subject_updated.emit()

    def _on_subject_deleted(self, subject_id: str):
        """Handle subject deleted from controller."""
        self._update_table_display()
        self.subject_updated.emit()

    def _on_keys_updated(self):
        """Handle keys updated from controller."""
        self._update_table_display()

    def _on_data_changed(self):
        """Handle data changed from controller."""
        # Data has changed, potentially save to file if needed
        pass

    def _update_table_display(self):
        """Update table display from controller data."""
        if not self._controller:
            return

        headers, rows = self._controller.get_table_data_matrix()

        if not headers or not rows:
            self.setRowCount(0)
            self.setColumnCount(0)
            return

        # Disconnect signals during update
        self._disconnect_table_widget()

        # Set table dimensions and headers
        self.setRowCount(len(rows))
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

        # Fill table with data
        for row_idx, row_data in enumerate(rows):
            for col_idx, cell_data in enumerate(row_data):
                item = QTableWidgetItem(str(cell_data))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_idx, col_idx, item)

        # Reconnect signals
        self._connect_table_widget()

