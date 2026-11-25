import json
from datetime import date

from cwf.filings import list_annual_filings


def cols(rows):
    keys = ["form", "accessionNumber", "filingDate", "reportDate"]
    return {k: [r[i] for r in rows] for i, k in enumerate(keys)}


class FakeClient:
    def __init__(self, pages):
        self.pages = pages

    def get_json(self, url, refresh=False):
        return json.loads(self.pages[url])


def idx(*names):
    return json.dumps({"directory": {"item": [{"name": n} for n in names]}})


SUB = "https://data.sec.gov/submissions/CIK0000313838.json"
PAGE = "https://data.sec.gov/submissions/CIK0000313838-submissions-001.json"
A = "https://www.sec.gov/Archives/edgar/data/313838/"


def sony_pages():
    recent = cols([("20-F", "0001-26-000001", "2026-06-18", "2026-03-31"),
                   ("6-K", "0001-26-000002", "2026-05-01", "2026-03-31"),
                   ("20-F/A", "0001-25-000009", "2025-09-01", "2025-03-31"),
                   ("20-F", "0001-25-000001", "2025-06-20", "2025-03-31")])
    old = cols([("20-F", "0001-18-000001", "2018-06-19", "2018-03-31"),
                ("20-F", "0001-14-000001", "2014-06-26", "2014-03-31")])
    return {
        SUB: json.dumps({"filings": {"recent": recent, "files": [{"name": "CIK0000313838-submissions-001.json"}]}}),
        PAGE: json.dumps(old),
        A + "000126000001/index.json": idx("d1_htm.xml", "d1.htm", "FilingSummary.xml"),
        A + "000125000001/index.json": idx("d2_htm.xml"),
        A + "000118000001/index.json": idx("FilingSummary.xml", "sne-20180331.xml", "sne-20180331_cal.xml",
                                           "sne-20180331_def.xml", "sne-20180331_lab.xml", "sne-20180331_pre.xml"),
    }


def test_merges_recent_and_paged_files():
    fs = list_annual_filings(FakeClient(sony_pages()), "sony", since_report_year=2015)
    assert [f.filing_date for f in fs] == [date(2018, 6, 19), date(2025, 6, 20), date(2026, 6, 18)]


def test_picks_inline_instance():
    fs = list_annual_filings(FakeClient(sony_pages()), "sony", since_report_year=2015)
    assert fs[-1].instance_url == A + "000126000001/d1_htm.xml"


def test_picks_legacy_instance_ignoring_linkbases():
    fs = list_annual_filings(FakeClient(sony_pages()), "sony", since_report_year=2015)
    assert fs[0].instance_url == A + "000118000001/sne-20180331.xml"


def test_excludes_amendments():
    fs = list_annual_filings(FakeClient(sony_pages()), "sony", since_report_year=2015)
    assert all("25-000009" not in f.accession for f in fs)
    assert all(f.company == "sony" for f in fs)


def test_submission_lists_are_refreshed_archives_are_not():
    seen = []

    class Recording(FakeClient):
        def get_json(self, url, refresh=False):
            seen.append((url, refresh))
            return super().get_json(url)

    list_annual_filings(Recording(sony_pages()), "sony", since_report_year=2015)
    assert all(r for u, r in seen if "/submissions/" in u)
    assert not any(r for u, r in seen if "/Archives/" in u)
