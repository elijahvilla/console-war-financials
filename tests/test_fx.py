from datetime import date
from pathlib import Path

import pytest

from cwf.fx import FRED_URL, load_dexjpus, period_average

SAMPLE = (Path(__file__).parent / "fixtures" / "dexjpus_sample.csv").read_bytes()


def rates():
    return load_dexjpus(lambda url: SAMPLE)


def test_fx_average_skips_blanks():
    r = rates()
    vals = [v for d, v in r.items() if date(2025, 4, 1) <= d <= date(2026, 3, 31)]
    assert all(isinstance(v, float) for v in vals)
    assert period_average(r, date(2025, 4, 1), date(2026, 3, 31)) == pytest.approx(sum(vals) / len(vals))
    assert len(vals) < 261  # blanks and "." were dropped


def test_fx_raises_on_sparse_period():
    with pytest.raises(ValueError, match="valid days"):
        period_average(rates(), date(2025, 4, 1), date(2025, 6, 30))


def test_fx_parses_fred_header():
    old = SAMPLE.replace(b"observation_date,DEXJPUS", b"DATE,DEXJPUS")
    assert load_dexjpus(lambda url: old) == rates()
    seen = []
    load_dexjpus(lambda url: seen.append(url) or SAMPLE)
    assert seen == [FRED_URL]
