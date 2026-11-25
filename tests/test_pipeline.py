import hashlib
import json
from datetime import date, timedelta

import openpyxl

from cwf.fx import FRED_URL
from cwf.pipeline import run

GNS = ("SegmentsAxis", "sony:GameAndNetworkServicesMember")
OPS = ("SegmentConsolidationItemsAxis", "ifrs-full:OperatingSegmentsMember")
EXT = ("SalesChannelsAxis", "sony:ExternalCustomersMember")


def instance(facts):
    ctx, body = [], []
    for i, (concept, start, end, dims, value, unit) in enumerate(facts):
        members = "".join(f'<xbrldi:explicitMember dimension="x:{a}">{m}</xbrldi:explicitMember>' for a, m in dims)
        ctx.append(f'<xbrli:context id="c{i}"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier>'
                   f'<xbrli:segment>{members}</xbrli:segment></xbrli:entity><xbrli:period>'
                   f'<xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate>'
                   f'</xbrli:period></xbrli:context>')
        body.append(f'<x:{concept} contextRef="c{i}" unitRef="{unit}" decimals="-6">{value}</x:{concept}>')
    return ('<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
            'xmlns:x="http://example.com/x" xmlns:iso4217="http://www.xbrl.org/2003/iso4217">'
            + "".join(ctx)
            + '<xbrli:unit id="USD"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
            + '<xbrli:unit id="JPY"><xbrli:measure>iso4217:JPY</xbrli:measure></xbrli:unit>'
            + "".join(body) + "</xbrli:xbrl>").encode()


def ms_facts(years):
    return [("RevenueFromContractWithCustomerExcludingAssessedTax", f"{y - 1}-07-01", f"{y}-06-30",
             [("ProductOrServiceAxis", "msft:GamingMember")], (10 + y - 2019) * 1e9, "USD") for y in years]


def sony_facts(years):
    out = []
    for y in years:
        s, e, k = f"{y - 1}-04-01", f"{y}-03-31", 1e9 * (1 + (y - 2019) / 10)
        out += [("Revenue", s, e, [GNS, OPS], 1000 * k, "JPY"),
                ("Revenue", s, e, [GNS, OPS, EXT], 900 * k, "JPY"),
                ("ProfitLossFromOperatingActivities", s, e, [GNS, OPS], 100 * k, "JPY")]
        for member, v in [("DigitalSoftwareAndAddOnContentMember", 500), ("NetworkServicesMember", 150),
                          ("HardwareAndOthersMember", 250)]:
            out.append(("Revenue", s, e, [GNS, OPS, EXT, ("ProductsAndServicesAxis", f"sony:{member}")], v * k, "JPY"))
    return out


def fred_csv():
    lines, d = ["observation_date,DEXJPUS"], date(2015, 1, 1)
    while d <= date(2026, 12, 31):
        if d.weekday() < 5:
            lines.append(f"{d},150.00")
        d += timedelta(days=1)
    return ("\n".join(lines) + "\n").encode()


def seed_cache(cache):
    pages = {FRED_URL: fred_csv()}
    plan = {"microsoft": ("0000789019", "10-K", [(2021, [2019, 2020, 2021]), (2023, [2021, 2022, 2023])], ms_facts),
            "sony": ("0000313838", "20-F", [(2022, [2020, 2021, 2022]), (2023, [2021, 2022, 2023])], sony_facts)}
    for company, (cik, form, filings, maker) in plan.items():
        recent = {"form": [], "accessionNumber": [], "filingDate": [], "reportDate": []}
        for fy, years in filings:
            acc = f"0000-{fy % 100:02d}-{cik[-4:]}"
            recent["form"].append(form)
            recent["accessionNumber"].append(acc)
            recent["filingDate"].append(f"{fy}-07-15")
            recent["reportDate"].append(f"{fy}-03-31")
            base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}"
            pages[base + "/index.json"] = json.dumps({"directory": {"item": [{"name": "i_htm.xml"}]}}).encode()
            pages[base + "/i_htm.xml"] = instance(maker(years))
        pages[f"https://data.sec.gov/submissions/CIK{cik}.json"] = json.dumps(
            {"filings": {"recent": recent, "files": []}}).encode()
    for url, body in pages.items():
        (cache / hashlib.sha256(url.encode()).hexdigest()).write_bytes(body)


def test_pipeline_offline_end_to_end(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    seed_cache(cache)
    summary = run(cache_dir=cache, reports_dir=tmp_path / "reports", charts_dir=tmp_path / "docs", offline=True)
    assert summary["checks"] == "passed"
    assert summary["filings"] == {"microsoft": 2, "sony": 2}
    assert summary["network_calls"] == 0
    wb = openpyxl.load_workbook(tmp_path / "reports" / "console_war_financials.xlsx")
    assert [r[0] for r in wb["Summary"].iter_rows(min_row=2, max_row=4, values_only=True)] == [2020, 2021, 2022]
    assert sorted(p.name for p in (tmp_path / "docs").glob("*.png")) == [
        "revenue_usd.png", "sony_margin.png", "sony_mix.png"]
