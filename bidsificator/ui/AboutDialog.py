from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from .._metadata import __version__, __authors__, __copyright__, __license__, __description__


class AboutDialog(QDialog):
    """
    About dialog showing application information and version.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Bidsificator")
        self.setModal(True)
        self.setFixedSize(400, 250)
        
        # Setup UI
        self._setup_ui()
    
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Application name
        app_label = QLabel("Bidsificator")
        app_font = QFont()
        app_font.setPointSize(20)
        app_font.setBold(True)
        app_label.setFont(app_font)
        app_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(app_label)
        
        # Version
        version_label = QLabel(f"Version {__version__}")
        version_font = QFont()
        version_font.setPointSize(12)
        version_label.setFont(version_font)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        # Description
        desc_label = QLabel(__description__)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Copyright
        copyright_label = QLabel(__copyright__)
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)
        
        # Author(s)
        if len(__authors__) == 1:
            author_text = f"Author: {__authors__[0]}"
        else:
            author_text = f"Authors: {', '.join(__authors__)}"
        author_label = QLabel(author_text)
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label.setWordWrap(True)
        layout.addWidget(author_label)
        
        # License
        license_label = QLabel(f"Licensed under {__license__}")
        license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(license_label)
        
        # Add stretch to fill remaining space
        layout.addStretch()
        
        self.setLayout(layout)