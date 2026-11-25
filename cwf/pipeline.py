"""End to end: find filings -> parse XBRL -> extract gaming rows -> FX -> DuckDB model -> checks -> Excel + charts.

python -m cwf.pipeline            # downloads anything not cached (needs SEC_USER_AGENT in .env)
python -m cwf.pipeline --offline  # cache only; fails on a miss
"""
import argparse
from functools import partial
from pathlib import Path

from cwf.charts import write_charts
from cwf.checks import run_checks
from cwf.db import build
from cwf.extract import extract
from cwf.filings import COMPANIES, list_annual_filings
from cwf.fx import load_dexjpus
from cwf.report_xlsx import write_report
from cwf.sec import SecClient, cached_get
from cwf.xbrl import parse_instance

ROOT = Path(__file__).resolve().parent.parent


def run(cache_dir: Path = ROOT / "data" / "cache", reports_dir: Path = ROOT / "reports",
        charts_dir: Path = ROOT / "docs", offline: bool = False, db_path: str = ":memory:") -> dict:
    client = SecClient(cache_dir=cache_dir, offline=offline)
    rows, filings = [], {}
    for company in COMPANIES:
        found = list_annual_filings(client, company)
        filings[company] = len(found)
        for f in found:
            rows += extract(f, parse_instance(client.get(f.instance_url)))
    fx = load_dexjpus(partial(cached_get, cache_dir=cache_dir, offline=offline))
    con = build(rows, fx, db_path)
    run_checks(con)  # raises DataQualityError listing every problem
    write_report(con, Path(reports_dir) / "console_war_financials.xlsx")
    write_charts(con, Path(charts_dir))
    return {
        "filings": filings,
        "rows": len(rows),
        "series_values": con.execute("SELECT count(*) FROM segment_year").fetchone()[0],
        "restatements": con.execute("SELECT count(*) FROM restatements").fetchone()[0],
        "checks": "passed",
        "network_calls": client.network_calls,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true", help="use only cached responses")
    s = run(offline=ap.parse_args().offline)
    print(f"filings used: {s['filings']}  extracted rows: {s['rows']}  values in model: {s['series_values']}")
    print(f"restatements logged: {s['restatements']}  checks: {s['checks']}  SEC network calls: {s['network_calls']}")
    print("wrote reports/console_war_financials.xlsx and docs/*.png")


if __name__ == "__main__":
    main()
