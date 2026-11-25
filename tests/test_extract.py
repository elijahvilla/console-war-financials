from datetime import date

from cwf.extract import extract
from cwf.filings import Filing
from cwf.xbrl import Fact

MS = Filing("microsoft", "0001-26-1", date(2026, 7, 29), date(2026, 6, 30), "u")
SONY = Filing("sony", "0001-26-2", date(2026, 6, 18), date(2026, 3, 31), "u")
P = "ProductOrServiceAxis"
REV = "RevenueFromContractWithCustomerExcludingAssessedTax"


def ms_fact(member, fy, value, start=None, end=None):
    return Fact(REV, value, "USD", start or date(fy - 1, 7, 1), end or date(fy, 6, 30),
                frozenset({(P, member)}), "-6")


def gns(*extra):
    return frozenset({("SegmentsAxis", "GameAndNetworkServicesMember"),
                      ("SegmentConsolidationItemsAxis", "OperatingSegmentsMember"), *extra})


def test_extract_handles_renamed_members():
    rows = extract(MS, [ms_fact("GamingMember", 2023, 15.466e9), ms_fact("XBOXMember", 2024, 21.503e9)])
    assert sorted((r.fiscal_year, r.metric, r.value) for r in rows) == [
        (2023, "revenue", 15.466e9), (2024, "revenue", 21.503e9)]


def test_extract_ignores_non_annual_periods():
    quarter = ms_fact("XBOXMember", 2026, 5e9, start=date(2026, 4, 1), end=date(2026, 6, 30))
    instant = Fact(REV, 1.0, "USD", None, date(2026, 6, 30), frozenset({(P, "XBOXMember")}), None)
    assert extract(MS, [quarter, instant]) == []


def test_exact_dim_count_prevents_double_count():
    total = Fact("Revenue", 4685.651e9, "JPY", date(2025, 4, 1), date(2026, 3, 31), gns(), "-6")
    external = Fact("Revenue", 4570.053e9, "JPY", date(2025, 4, 1), date(2026, 3, 31),
                    gns(("SalesChannelsAxis", "ExternalCustomersMember")), "-6")
    rows = {r.metric: r.value for r in extract(SONY, [total, external])}
    assert rows == {"revenue": 4685.651e9, "revenue_external": 4570.053e9}


def test_basis_from_concept():
    gaap = Fact("OperatingIncomeLoss", 342.192e9, "JPY", date(2020, 4, 1), date(2021, 3, 31),
                frozenset({("StatementBusinessSegmentsAxis", "GameAndNetworkServicesMember"),
                           ("ConsolidationItemsAxis", "OperatingSegmentsMember")}), "-6")
    ifrs = Fact("ProfitLossFromOperatingActivities", 463.258e9, "JPY", date(2025, 4, 1), date(2026, 3, 31), gns(), "-6")
    rows = {r.fiscal_year: (r.metric, r.basis, r.currency) for r in extract(SONY, [gaap, ifrs])}
    assert rows == {2021: ("operating_income", "us-gaap", "JPY"), 2026: ("operating_income", "ifrs", "JPY")}


def test_fiscal_year_is_period_end_year():
    f = Fact("Revenue", 1.0, "JPY", date(2025, 4, 1), date(2026, 3, 31), gns(), "-6")
    assert extract(SONY, [f])[0].fiscal_year == 2026


def test_identical_duplicates_collapse():
    f = Fact("Revenue", 1.0, "JPY", date(2025, 4, 1), date(2026, 3, 31), gns(), "-6")
    assert len(extract(SONY, [f, f])) == 1


def test_rows_carry_provenance():
    r = extract(MS, [ms_fact("XBOXMember", 2026, 21.79e9)])[0]
    assert (r.accession, r.concept, r.filing_date) == ("0001-26-1", REV, date(2026, 7, 29))
