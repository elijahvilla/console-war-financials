from datetime import date
from pathlib import Path

from cwf.xbrl import parse_instance

XML = (Path(__file__).parent / "fixtures" / "mini_instance.xml").read_bytes()


def facts():
    return parse_instance(XML)


def test_parses_dimensional_fact():
    gns = [f for f in facts() if f.concept == "Revenue" and f.dims]
    assert len(gns) == 1
    f = gns[0]
    assert f.value == 4685651000000
    assert f.start == date(2025, 4, 1) and f.end == date(2026, 3, 31)
    assert ("SegmentsAxis", "GameAndNetworkServicesMember") in f.dims
    assert len(f.dims) == 2


def test_instant_context_has_no_start():
    a = [f for f in facts() if f.concept == "Assets"][0]
    assert a.start is None and a.end == date(2026, 3, 31)


def test_unit_resolved_to_currency_code():
    assert {f.unit for f in facts()} == {"JPY"}


def test_nil_and_text_facts_dropped():
    names = {f.concept for f in facts()}
    assert "ProfitLoss" not in names and "DocumentType" not in names


def test_prefix_stripped_from_members():
    for f in facts():
        for axis, member in f.dims:
            assert ":" not in axis and ":" not in member
