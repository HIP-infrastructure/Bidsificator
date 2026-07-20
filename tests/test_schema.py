#!/usr/bin/env python3
"""BIDS schema parsing tests.

Behavioural checks on the schema manager. Exact "shape" counts (datatype count,
entity count, per-datatype recommended-field floors) live in
``test_schema_sanity.py``, which is the single source of truth for those numbers.
"""

from bidsificator.core.schema import BidsSchemaManager


def test_schema_versions_are_populated():
    manager = BidsSchemaManager.get_instance()
    assert manager.get_bids_version()
    assert manager.get_schema_version()


def test_entities_and_datatypes_are_parsed():
    manager = BidsSchemaManager.get_instance()
    # A non-empty parse is the key regression guard: the classic failure mode is
    # the parser silently returning nothing.
    assert len(manager.entities) > 0
    assert len(manager.datatypes) > 0
    assert "ieeg" in manager.datatypes


def test_ieeg_datatype_structure():
    manager = BidsSchemaManager.get_instance()
    ieeg = manager.get_datatype("ieeg")
    assert ieeg is not None
    assert ieeg.suffixes, "ieeg should declare suffixes"
    assert ieeg.extensions, "ieeg should declare extensions"

    requirements = ieeg.metadata_requirements
    assert requirements.get("required") is not None
    assert requirements.get("recommended"), "ieeg should have recommended metadata fields"


def test_entity_value_validation():
    manager = BidsSchemaManager.get_instance()
    # Well-formed label / index values are accepted.
    assert manager.validate_entity_value("sub", "01")
    assert manager.validate_entity_value("run", "1")
    # A trailing hyphen is not a valid label.
    assert not manager.validate_entity_value("sub", "invalid-")


def test_schema_info_counts_are_consistent():
    manager = BidsSchemaManager.get_instance()
    info = manager.get_schema_info()
    assert info.get("num_entities") == len(manager.entities)
    assert info.get("num_datatypes") == len(manager.datatypes)
