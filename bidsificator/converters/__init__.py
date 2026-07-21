"""
BIDS Format Converters

Converts proprietary neuroimaging formats to BIDS-compliant formats.
"""

from .base import FormatConverter
from .registry import ConverterRegistry

__all__ = ['FormatConverter', 'ConverterRegistry']
