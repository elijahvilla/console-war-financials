"""Map raw XBRL facts to tidy gaming-segment rows using tag_map.yaml."""
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

TAG_MAP = Path(__file__).resolve().parent / "tag_map.yaml"
ANNUAL_DAYS = (330, 380)


@dataclass(frozen=True)
class Row:
    company: str
    fiscal_year: int
    period_start: date
    period_end: date
    metric: str
    value: float
    currency: str
    accession: str
    filing_date: date
    concept: str
    basis: str


@lru_cache(maxsize=1)
def load_tag_map() -> dict:
    return yaml.safe_load(TAG_MAP.read_text(encoding="utf-8"))


def _matches(rule: dict, fact) -> bool:
    if fact.concept not in rule["concepts"] or len(fact.dims) != rule["exactly_dims"]:
        return False
    dims = dict(fact.dims)
    return all(dims.get(axis) in members for axis, members in rule["require"].items())


def extract(filing, facts) -> list[Row]:
    tm = load_tag_map()
    rules = tm[filing.company]
    out = {}
    for f in facts:
        if f.start is None or f.value is None:
            continue
        if not ANNUAL_DAYS[0] <= (f.end - f.start).days <= ANNUAL_DAYS[1]:
            continue
        for metric, metric_rules in rules.items():
            if any(_matches(r, f) for r in metric_rules):
                row = Row(filing.company, f.end.year, f.start, f.end, metric, f.value, f.unit or "",
                          filing.accession, filing.filing_date, f.concept, tm["basis"][f.concept])
                out[row] = None  # identical duplicates (same fact in two tables) collapse
    return list(out)
