# Bidsificator

A PyQt6 desktop application for managing neuroimaging data in BIDS (Brain Imaging Data Structure) format.

## Overview

Bidsificator helps neuroscience researchers organize brain imaging data (iEEG, EEG, MRI) according to the BIDS standard through an intuitive graphical interface. It automates the conversion, validation, and metadata management required for BIDS-compliant datasets.

## Features

- 🧠 **Multiple Modalities** - Support for iEEG, EEG, MRI (anatomical, functional, diffusion), and more
- 📋 **BIDS Compliance** - Automatic validation and schema-driven file generation (BIDS 1.10.0)
- 🔄 **File Conversion** - Convert TRC, DICOM, and other formats to BIDS-compliant formats
- 🏥 **Clinical Annotations** - Add SEEG electrode annotations from Excel files with clinical data
- ✅ **Validation** - Real-time BIDS validation with detailed error reporting
- 🎨 **User-Friendly GUI** - Intuitive PyQt6 interface for all operations
- 🚀 **Batch Processing** - Import multiple subjects and sessions efficiently
- 🔌 **REST API** - Programmatic access via Flask-based API server

[📖 **Full Documentation**](docs/README.md) | [🚀 **Quick Start Guide**](docs/features/contact-labeling.md)

## Quick Start

### Installation

```bash
# Install dependencies with Poetry
poetry install

# Run the GUI application
poetry run bidsificator

# Or run the API server (debug mode)
poetry run bidsificator-api
```

### Basic Usage

1. **Create Dataset** - Create a new BIDS dataset or open an existing one
2. **Import Files** - Import neuroimaging files (TRC, EDF, DICOM, NIfTI)
3. **Add Metadata** - Edit subject/session metadata and add clinical annotations
4. **Validate** - Check BIDS compliance with automatic validation
5. **Export** - Generate BIDS-compliant dataset ready for sharing

## Documentation

- 📚 [**User Guides**](docs/features/) - How to use Bidsificator features
- 🏗️ [**Architecture**](docs/architecture/) - Technical design and implementation
- 📖 [**Full Documentation**](docs/README.md) - Complete documentation hub

## Development

Use `poetry` (installed via `pipx`) to setup the virtual env and run it nicely for you.

```console
# Pick a valid Python3 version, e.g. 3.10 or 3.11
$ poetry env use $(pyenv which python3.10)

$ poetry env use $(pyenv which python3.11)

$ poetry install
```

Running the UI.

```console
$ poetry run bidsificator
```

Running the web server (in debug mode), use `gunicorn` or else in production.

```console
$ poetry run bidsificator-api
```

### UI

Opening the Qt designer with the form.

```console
$ poetry run make design
```

And then rebuilding the Python file from it.

```console
$ poetry run make build-ui
```

## Requirements

- Python 3.10-3.12
- PyQt6
- Poetry (for dependency management)

## Contributing

We welcome contributions! For details on:
- Setting up the development environment - see [Development](#development) section
- Code style and conventions - see [CLAUDE.md](CLAUDE.md)
- Submitting pull requests - open an issue first to discuss
- Reporting issues - use GitHub Issues

## License

[Add your license information here]

## Citation

If you use Bidsificator in your research, please cite:

```
[Add citation information]
```

## Acknowledgments

This project has received funding from the Swiss State Secretariat for Education, Research and Innovation (SERI) under contract number 23.00638, as part of the Horizon Europe project “EBRAINS 2.0”.
