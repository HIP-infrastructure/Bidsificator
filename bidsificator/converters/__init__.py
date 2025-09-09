"""
BIDS Format Converters

Converts proprietary neuroimaging formats to BIDS-compliant formats.
"""

from .base import FormatConverter, FileAnalysis
from .registry import ConverterRegistry

__all__ = ['FormatConverter', 'FileAnalysis', 'ConverterRegistry']