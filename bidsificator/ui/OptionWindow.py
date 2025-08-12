from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QMessageBox,
    QFileDialog,
    QInputDialog,
)
from PyQt6.QtCore import QStandardPaths, QItemSelectionModel
from ..controllers.OptionController import OptionController
from ..forms.OptionWindow_ui import Ui_OptionsForm


class OptionWindow(QWidget, Ui_OptionsForm):
    """
    Window for managing application options/configuration.
    Acts as the View in the MVC pattern, delegating business logic to OptionController.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Option Window.
        
        Args:
            config_path: Optional path to configuration file. 
                        If None, uses default path.
        """
        super(QWidget, self).__init__()
        self.setupUi(self)
        
        # Initialize controller with optional config path
        # This maintains backward compatibility while allowing dependency injection
        self.controller = OptionController(config_path or 'bidsificator/config/config.yaml')
        
        # Connect UI signals to handlers
        self._connect_signals()
        
        # Initialize UI with current model state
        self._initialize_ui()
    
    def _connect_signals(self):
        """Connect UI signals to their handlers."""
        # Database related signals
        self.separatedDbCheckBox.stateChanged.connect(self._on_separated_db_changed)
        self.AnatDbBrowse.clicked.connect(self._on_anat_db_browse)
        self.AnatDbLineEdit.editingFinished.connect(self._on_anat_db_edited)
        self.FuncDbBrowse.clicked.connect(self._on_func_db_browse)
        self.FuncDbLineEdit.editingFinished.connect(self._on_func_db_edited)
        
        # Subject pattern signal
        self.SubPatternLineEdit.editingFinished.connect(self._on_subject_pattern_edited)
        
        # Data type list signals
        self.listWidget.clicked.connect(self._on_data_type_selected)
        self.listWidget.itemSelectionChanged.connect(self._on_data_type_selected)
        
        # Data type buttons
        self.AddDataTypePushButton.clicked.connect(self._on_add_data_type)
        self.RemoveDataTypePushButton.clicked.connect(self._on_remove_data_type)
        
        # Data type field signals
        self.DescriptionLineEdit.editingFinished.connect(self._on_description_edited)
        self.DirectoryLineEdit.editingFinished.connect(self._on_directory_edited)
        self.FileExtLineEdit.editingFinished.connect(self._on_extensions_edited)
        
        # Dialog buttons
        self.OkPushButton.clicked.connect(self._on_ok_clicked)
        self.CancelPushButton.clicked.connect(self.close)
    
    def _initialize_ui(self):
        """Initialize UI with current model state."""
        # Initialize database options
        separated = self.controller.are_databases_separated()
        self.separatedDbCheckBox.setChecked(separated)
        self._update_db_visibility(separated)
        
        self.AnatDbLineEdit.setText(self.controller.get_anatomical_db_path())
        self.FuncDbLineEdit.setText(self.controller.get_functional_db_path())
        
        # Initialize subject pattern
        self.SubPatternLineEdit.setText(self.controller.get_subject_pattern())
        
        # Initialize data types list
        for data_type_name in self.controller.get_data_type_names():
            self.listWidget.addItem(data_type_name)
        
        self._update_data_type_fields_state()
    
    def _update_db_visibility(self, show_separated: bool):
        """Update visibility of functional database fields."""
        self.FuncLabel.setVisible(show_separated)
        self.FuncDbLineEdit.setVisible(show_separated)
        self.FuncDbBrowse.setVisible(show_separated)
    
    def _update_data_type_fields_state(self):
        """Enable/disable data type fields based on selection."""
        has_selection = self.listWidget.count() > 0
        self.DescriptionLineEdit.setEnabled(has_selection)
        self.DirectoryLineEdit.setEnabled(has_selection)
        self.FileExtLineEdit.setEnabled(has_selection)
        
        if not has_selection:
            self.DescriptionLineEdit.clear()
            self.DirectoryLineEdit.clear()
            self.FileExtLineEdit.clear()
    
    # Database path handlers
    
    def _on_separated_db_changed(self):
        """Handle separated database checkbox change."""
        separated = self.separatedDbCheckBox.isChecked()
        self.controller.set_databases_separated(separated)
        
        if not separated:
            # When unchecking, sync functional with anatomical
            anat_path = self.controller.get_anatomical_db_path()
            self.FuncDbLineEdit.setText(anat_path)
        
        self._update_db_visibility(separated)
    
    def _on_anat_db_browse(self):
        """Handle anatomical database browse button."""
        current_path = self.controller.get_anatomical_db_path()
        start_dir = current_path if current_path else QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DesktopLocation
        )
        
        db_path = QFileDialog.getExistingDirectory(
            self, 
            "Select anatomical database directory", 
            start_dir
        )
        
        if db_path:
            self.AnatDbLineEdit.setText(db_path)
            self.controller.set_anatomical_db_path(db_path)
    
    def _on_anat_db_edited(self):
        """Handle anatomical database path editing."""
        path = self.AnatDbLineEdit.text()
        self.controller.set_anatomical_db_path(path)
    
    def _on_func_db_browse(self):
        """Handle functional database browse button."""
        current_path = self.controller.get_functional_db_path()
        start_dir = current_path if current_path else QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DesktopLocation
        )
        
        db_path = QFileDialog.getExistingDirectory(
            self, 
            "Select functional database directory", 
            start_dir
        )
        
        if db_path:
            self.FuncDbLineEdit.setText(db_path)
            self.controller.set_functional_db_path(db_path)
    
    def _on_func_db_edited(self):
        """Handle functional database path editing."""
        path = self.FuncDbLineEdit.text()
        self.controller.set_functional_db_path(path)
    
    # Subject pattern handler
    
    def _on_subject_pattern_edited(self):
        """Handle subject pattern editing."""
        pattern = self.SubPatternLineEdit.text()
        self.controller.set_subject_pattern(pattern)
    
    # Data type handlers
    
    def _on_data_type_selected(self):
        """Handle data type selection in list."""
        current_item = self.listWidget.currentItem()
        if current_item is None:
            return
        
        selected_name = current_item.text()
        data_type = self.controller.get_data_type(selected_name)
        
        if data_type:
            self.DescriptionLineEdit.setText(data_type.get('description', ''))
            self.DirectoryLineEdit.setText(data_type.get('directory', ''))
            extensions_str = self.controller.format_extensions_for_display(selected_name)
            self.FileExtLineEdit.setText(extensions_str)
    
    def _on_add_data_type(self):
        """Handle add data type button."""
        name, ok = QInputDialog.getText(
            self, 
            "Data type Name", 
            "Enter a name for the data type"
        )
        
        if ok and name:
            if self.controller.add_data_type(name):
                self.listWidget.addItem(name)
                # Select the newly added item
                self.listWidget.setCurrentRow(
                    self.listWidget.count() - 1, 
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                )
                self._update_data_type_fields_state()
            else:
                QMessageBox.warning(
                    self, 
                    'Duplicate Name', 
                    f'A data type named "{name}" already exists.'
                )
    
    def _on_remove_data_type(self):
        """Handle remove data type button."""
        row = self.listWidget.currentRow()
        if row == -1:
            return
        
        selected_item = self.listWidget.currentItem()
        if selected_item:
            name = selected_item.text()
            if self.controller.remove_data_type(name):
                self.listWidget.takeItem(row)
                
                # Select another item if available
                if self.listWidget.count() > 0:
                    new_row = min(row, self.listWidget.count() - 1)
                    self.listWidget.setCurrentRow(
                        new_row,
                        QItemSelectionModel.SelectionFlag.ClearAndSelect
                    )
                
                self._update_data_type_fields_state()
    
    def _on_description_edited(self):
        """Handle description field editing."""
        if self.listWidget.currentRow() == -1:
            return
        
        selected_item = self.listWidget.currentItem()
        if selected_item:
            name = selected_item.text()
            description = self.DescriptionLineEdit.text()
            self.controller.update_data_type_description(name, description)
    
    def _on_directory_edited(self):
        """Handle directory field editing."""
        if self.listWidget.currentRow() == -1:
            return
        
        selected_item = self.listWidget.currentItem()
        if selected_item:
            name = selected_item.text()
            directory = self.DirectoryLineEdit.text()
            self.controller.update_data_type_directory(name, directory)
    
    def _on_extensions_edited(self):
        """Handle file extensions field editing."""
        if self.listWidget.currentRow() == -1:
            return
        
        selected_item = self.listWidget.currentItem()
        if selected_item:
            name = selected_item.text()
            extensions_str = self.FileExtLineEdit.text()
            
            success, error_msg = self.controller.update_data_type_extensions(name, extensions_str)
            if not success:
                QMessageBox.critical(
                    self, 
                    'Invalid file extensions', 
                    error_msg
                )
                # Restore previous value
                extensions_str = self.controller.format_extensions_for_display(name)
                self.FileExtLineEdit.setText(extensions_str)
    
    def _on_ok_clicked(self):
        """Handle OK button click."""
        # Trigger any pending editingFinished signals
        self.setFocus()
        
        # Save configuration through controller
        if self.controller.save_configuration():
            self.close()
        else:
            QMessageBox.critical(
                self,
                'Save Error',
                'Failed to save configuration. Please check file permissions.'
            )
    
