<p align="center">
  <img src="docs/images/logo.png" alt="Bidsificator logo" width="200">
</p>

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
- 🔌 **REST API** - Programmatic access via a Flask-based API server (currently dormant — no active consumers)

[📖 **Full Documentation**](docs/README.md) | [🚀 **Quick Start Guide**](#quick-start)

## Quick Start

### Installation

```bash
# Install dependencies with Poetry
poetry install

# Run the GUI application
poetry run bidsificator

# Or run the API server (dormant; localhost-only, debugger off by default)
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
# Pick a supported Python version (3.11–3.13)
$ poetry env use $(pyenv which python3.11)

$ poetry env use $(pyenv which python3.12)

$ poetry install
```

Running the UI.

```console
$ poetry run bidsificator
```

Running the web server. It is **dormant** (no active consumers) and starts
localhost-only with the Werkzeug debugger **off**. Enable debug mode explicitly
for local development; use `gunicorn` (or similar) in production.

```console
# Safe default (127.0.0.1:5000, debugger off):
$ poetry run bidsificator-api

# Development, with the debugger enabled:
$ BIDSIFICATOR_API_DEBUG=1 poetry run bidsificator-api
```

Overridable via `BIDSIFICATOR_API_HOST` and `BIDSIFICATOR_API_PORT`.

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

- Python 3.11-3.13
- PyQt6
- Poetry (for dependency management)

## Contributing

We welcome contributions! For details on:
- Setting up the development environment - see [Development](#development) section
- Code style and conventions - see [CLAUDE.md](CLAUDE.md)
- Submitting pull requests - open an issue first to discuss
- Reporting issues - use GitHub Issues

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Citation

If you use Bidsificator in your research, please cite:

```
[Add citation information]
```

## Acknowledgments

This project has received funding from the Swiss State Secretariat for Education, Research and Innovation (SERI) under contract number 23.00638, as part of the Horizon Europe project “EBRAINS 2.0”.
