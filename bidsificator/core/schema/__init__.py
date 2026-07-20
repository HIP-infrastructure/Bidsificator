"""
BIDS Schema management package

This package provides dynamic BIDS validation and naming based on the official BIDS schema.
"""

from .models import BidsDatatype, BidsEntity, EntityFormat
from .parser import BidsSchemaParser
from .schema_manager import BidsSchemaManager

__all__ = [
    'BidsSchemaManager',
    'BidsEntity',
    'BidsDatatype',
    'EntityFormat',
    'BidsSchemaParser'
]
