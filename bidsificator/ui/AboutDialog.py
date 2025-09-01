import os
import re
import sys
from importlib.metadata import metadata, PackageNotFoundError
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class AboutDialog(QDialog):
    """
    About dialog showing application information and version.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Bidsificator")
        self.setModal(True)
        self.setFixedSize(400, 240)
        
        # Get metadata from package or pyproject.toml
        self.metadata = self._get_metadata()
        
        # Setup UI
        self._setup_ui()
    
    def _get_metadata(self) -> dict:
        """Get metadata from package or pyproject.toml."""
        metadata_dict = {}
        
        try:
            # Try to get metadata from installed package
            pkg_metadata = metadata("bidsificator")
            metadata_dict["version"] = pkg_metadata["Version"]
            metadata_dict["authors"] = self._parse_authors_from_metadata(pkg_metadata.get("Author", ""))
            metadata_dict["license"] = pkg_metadata.get("License", "Unknown")
            metadata_dict["copyright"] = None  # Not in package metadata
            # Fall back to pyproject.toml even if package is installed for copyright
            metadata_dict.update(self._get_additional_metadata())
        except PackageNotFoundError:
            # Fallback: read from pyproject.toml during development
            pyproject_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "pyproject.toml"
            )
            
            try:
                # For Python 3.11+, use built-in tomllib
                if sys.version_info >= (3, 11):
                    import tomllib
                    with open(pyproject_path, "rb") as f:
                        data = tomllib.load(f)
                        poetry_data = data.get("tool", {}).get("poetry", {})
                        metadata_dict["version"] = poetry_data.get("version", "Unknown")
                        metadata_dict["authors"] = self._parse_authors_from_poetry(poetry_data.get("authors", []))
                        metadata_dict["license"] = poetry_data.get("license", "Unknown")
                        # Check for custom copyright field in tool.bidsificator section
                        bidsificator_data = data.get("tool", {}).get("bidsificator", {})
                        metadata_dict["copyright"] = bidsificator_data.get("copyright")
                else:
                    # For Python 3.10, use regex parsing
                    with open(pyproject_path, "r") as f:
                        content = f.read()
                        
                        # Extract version
                        version_match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
                        metadata_dict["version"] = version_match.group(1) if version_match else "Unknown"
                        
                        # Extract authors (can be multiple lines)
                        authors = []
                        authors_match = re.findall(r'^authors\s*=\s*\[(.*?)\]', content, re.MULTILINE | re.DOTALL)
                        if authors_match:
                            # Parse author entries
                            author_entries = re.findall(r'"([^"]+)"', authors_match[0])
                            authors = self._parse_authors_from_poetry(author_entries)
                        metadata_dict["authors"] = authors if authors else ["Unknown"]
                        
                        # Extract license
                        license_match = re.search(r'^license\s*=\s*"([^"]+)"', content, re.MULTILINE)
                        metadata_dict["license"] = license_match.group(1) if license_match else "Unknown"
                        
                        # Extract copyright from tool.bidsificator section
                        copyright_match = re.search(r'^\[tool\.bidsificator\].*?^copyright\s*=\s*"([^"]+)"', content, re.MULTILINE | re.DOTALL)
                        metadata_dict["copyright"] = copyright_match.group(1) if copyright_match else None
            except (FileNotFoundError, KeyError):
                metadata_dict["version"] = "Unknown"
                metadata_dict["authors"] = ["Unknown"]
                metadata_dict["license"] = "Unknown"
                metadata_dict["copyright"] = None
        
        return metadata_dict
    
    def _get_additional_metadata(self) -> dict:
        """Get additional metadata from pyproject.toml, including complete authors list."""
        additional = {}
        pyproject_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "pyproject.toml"
        )
        
        try:
            # For Python 3.11+, use built-in tomllib
            if sys.version_info >= (3, 11):
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    
                    # Always get complete authors list from pyproject.toml
                    poetry_data = data.get("tool", {}).get("poetry", {})
                    if "authors" in poetry_data:
                        additional["authors"] = self._parse_authors_from_poetry(poetry_data["authors"])
                    
                    # Get copyright from custom section
                    bidsificator_data = data.get("tool", {}).get("bidsificator", {})
                    if "copyright" in bidsificator_data:
                        additional["copyright"] = bidsificator_data["copyright"]
            else:
                # For Python 3.10, use regex parsing
                with open(pyproject_path, "r") as f:
                    content = f.read()
                    
                    # Extract complete authors list
                    authors = []
                    authors_match = re.findall(r'^authors\s*=\s*\[(.*?)\]', content, re.MULTILINE | re.DOTALL)
                    if authors_match:
                        author_entries = re.findall(r'"([^"]+)"', authors_match[0])
                        authors = self._parse_authors_from_poetry(author_entries)
                        additional["authors"] = authors
                    
                    # Extract copyright
                    copyright_match = re.search(r'^\[tool\.bidsificator\].*?^copyright\s*=\s*"([^"]+)"', content, re.MULTILINE | re.DOTALL)
                    if copyright_match:
                        additional["copyright"] = copyright_match.group(1)
        except (FileNotFoundError, KeyError):
            pass
            
        return additional
    
    def _parse_authors_from_poetry(self, authors_list):
        """Parse authors from poetry format (list of 'Name <email>' strings)."""
        parsed_authors = []
        for author in authors_list:
            # Remove email if present
            if '<' in author:
                name = author.split('<')[0].strip()
            else:
                name = author.strip()
            if name:
                parsed_authors.append(name)
        return parsed_authors if parsed_authors else ["Unknown"]
    
    def _parse_authors_from_metadata(self, author_string):
        """Parse authors from package metadata."""
        if not author_string:
            return ["Unknown"]
        # Simple parsing, might need enhancement for multiple authors
        return [author_string]
    
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
        version_label = QLabel(f"Version {self.metadata.get('version', 'Unknown')}")
        version_font = QFont()
        version_font.setPointSize(12)
        version_label.setFont(version_font)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        # Copyright - use from metadata if available, otherwise hardcoded default
        copyright_text = self.metadata.get("copyright", "Unknown")
        copyright_label = QLabel(copyright_text)
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)
        
        # Author(s)
        authors = self.metadata.get("authors", ["Unknown"])
        if len(authors) == 1:
            author_text = f"Author: {authors[0]}"
        else:
            author_text = f"Authors: {', '.join(authors)}"
        author_label = QLabel(author_text)
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label.setWordWrap(True)
        layout.addWidget(author_label)
        
        # License
        license_text = self.metadata.get("license", "Unknown")
        license_label = QLabel(f"Licensed under {license_text}")
        license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(license_label)
        
        # Add stretch to fill remaining space
        layout.addStretch()
        
        self.setLayout(layout)