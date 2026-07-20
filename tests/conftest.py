"""Shared pytest fixtures for the Bidsificator test suite."""

import pytest


@pytest.fixture(scope="session")
def schema_manager():
    """The BIDS schema manager singleton, loaded once per test session."""
    from bidsificator.core.schema import BidsSchemaManager
    return BidsSchemaManager.get_instance()
