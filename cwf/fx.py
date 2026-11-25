"""USD/JPY from the Federal Reserve (FRED series DEXJPUS: yen per US dollar, daily noon buying rate).

Keyless CSV download. Holidays come through as "." or blank and are skipped.
"""
import csv
import io
from datetime import date
from typing import Callable

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXJPUS"
MIN_VALID_DAYS = 200


def load_dexjpus(client_get: Callable[[str], bytes]) -> dict[date, float]:
    text = client_get(FRED_URL).decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    if len(header) < 2 or header[1].strip() != "DEXJPUS":
        raise ValueError(f"unexpected FRED header: {header}")
    out = {}
    for row in reader:
        if len(row) < 2 or row[1].strip() in ("", "."):
            continue
        out[date.fromisoformat(row[0].strip())] = float(row[1])
    return out


def period_average(rates: dict[date, float], start: date, end: date) -> float:
    vals = [v for d, v in rates.items() if start <= d <= end]
    if len(vals) < MIN_VALID_DAYS:
        raise ValueError(f"only {len(vals)} valid days of USD/JPY for {start}..{end} (need {MIN_VALID_DAYS})")
    return sum(vals) / len(vals)
