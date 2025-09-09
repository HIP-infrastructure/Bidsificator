"""
BIDS Schema management package

This package provides dynamic BIDS validation and naming based on the official BIDS schema.
"""

from .schema_manager import BidsSchemaManager
from .models import BidsEntity, BidsDatatype, EntityFormat
from .parser import BidsSchemaParser

__all__ = [
    'BidsSchemaManager',
    'BidsEntity', 
    'BidsDatatype',
    'EntityFormat',
    'BidsSchemaParser'
]