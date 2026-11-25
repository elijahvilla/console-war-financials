"""Find each company's annual filings (10-K / 20-F) on EDGAR and the XBRL instance inside each one."""
from dataclasses import dataclass
from datetime import date

COMPANIES = {"microsoft": ("0000789019", "10-K"), "sony": ("0000313838", "20-F")}
LINKBASE_SUFFIXES = ("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml")


@dataclass(frozen=True)
class Filing:
    company: str
    accession: str
    filing_date: date
    report_date: date
    instance_url: str


def _rows(block: dict):
    for i in range(len(block.get("form", []))):
        yield block["form"][i], block["accessionNumber"][i], block["filingDate"][i], block["reportDate"][i]


def _pick_instance(names: list[str]) -> str | None:
    inline = [n for n in names if n.endswith("_htm.xml")]
    if inline:
        return inline[0]
    legacy = [n for n in names if n.endswith(".xml") and not n.endswith(LINKBASE_SUFFIXES)
              and n != "FilingSummary.xml"]
    return legacy[0] if legacy else None


def list_annual_filings(client, company: str, since_report_year: int = 2015) -> list[Filing]:
    cik, form = COMPANIES[company]
    sub = client.get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    rows = list(_rows(sub["filings"]["recent"]))
    for page in sub["filings"].get("files", []):
        rows += list(_rows(client.get_json(f"https://data.sec.gov/submissions/{page['name']}")))
    out = {}
    for f, acc, filed, report in rows:
        if f != form or not report or date.fromisoformat(report).year < since_report_year:
            continue
        base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}"
        names = [i["name"] for i in client.get_json(base + "/index.json")["directory"]["item"]]
        inst = _pick_instance(names)
        if inst is None:  # pre-XBRL filing
            continue
        out[acc] = Filing(company, acc, date.fromisoformat(filed), date.fromisoformat(report), f"{base}/{inst}")
    return sorted(out.values(), key=lambda x: x.filing_date)
