#!/usr/bin/env python3
"""Schema sanity / regression checks.

This is the single source of truth for the schema "shape" numbers that used to
live (and go stale) in CLAUDE.md. Its main job is to fail loudly if the parser
regresses — the classic failure mode is `_extract_metadata_requirements()`
silently returning nothing, which shows up as 0 datatypes / 0 recommended
fields. Structural counts are asserted exactly; per-datatype metadata counts use
floors so a schema bump doesn't cause spurious failures.

Verified against the bundled BIDS 1.10.1 / schema 1.1.0 on 2026-07-20.

Run:
    poetry run pytest tests/test_schema_sanity.py
"""

from bidsificator.core.bids_constants import get_entity_order
from bidsificator.core.schema import BidsSchemaManager


def test_schema_versions():
    m = BidsSchemaManager.get_instance()
    assert m.get_bids_version() == "1.10.1"
    assert m.get_schema_version() == "1.1.0"


def test_datatype_count_is_exact():
    # Structural: a change here means the schema really changed. If this is 0,
    # the parser is broken.
    m = BidsSchemaManager.get_instance()
    assert len(m.datatypes) == 15, (
        f"expected 15 datatypes, got {len(m.datatypes)} "
        f"(parser regression if 0): {sorted(m.datatypes)}"
    )


def test_entity_order_count_is_exact():
    assert len(get_entity_order()) == 31


def test_recommended_metadata_floors():
    # Floors, not exact counts: catches "parser returns empty" without breaking
    # on a minor schema bump that adds/removes a field or two.
    m = BidsSchemaManager.get_instance()
    floors = {"ieeg": 20, "anat": 35, "func": 35, "dwi": 30}
    for datatype, floor in floors.items():
        d = m.get_datatype(datatype)
        assert d is not None, f"datatype {datatype!r} missing from schema"
        count = len(d.get_recommended_metadata())
        assert count >= floor, (
            f"{datatype} recommended metadata dropped to {count} "
            f"(floor {floor}) — likely a parser regression"
        )


def test_default_suffix_selection():
    from bidsificator.core.bids_constants import get_default_suffix_for_datatype
    assert get_default_suffix_for_datatype("ieeg") == "ieeg"
    assert get_default_suffix_for_datatype("anat") == "T1w"
