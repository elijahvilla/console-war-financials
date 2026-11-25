from datetime import date

import pytest

from cwf.checks import DataQualityError, run_checks
from cwf.db import build
from tests.helpers import clean_sony_year, flat_fx, ms, sony


def clean_rows():
    return [ms(fy, 10e9 + fy) for fy in range(2019, 2027)] + [r for fy in (2025, 2026) for r in clean_sony_year(fy)]


def test_checks_pass_on_clean_fixture():
    run_checks(build(clean_rows(), flat_fx()))


def test_checks_flag_bucket_mismatch():
    rows = [r for r in clean_rows() if not (r.fiscal_year == 2026 and r.metric == "rev_hardware_other")]
    rows.append(sony(2026, "rev_hardware_other", 300.0))  # buckets now sum to 950 vs external 900
    with pytest.raises(DataQualityError, match="bucket"):
        run_checks(build(rows, flat_fx()))


def test_checks_flag_year_gap():
    rows = [r for r in clean_rows() if not (r.company == "microsoft" and r.fiscal_year == 2022)]
    with pytest.raises(DataQualityError, match="gap"):
        run_checks(build(rows, flat_fx()))


def test_checks_flag_conflict_inside_latest_filing():
    rows = clean_rows() + [sony(2026, "revenue", 999.0)]  # same filing, second value
    with pytest.raises(DataQualityError, match="conflict"):
        run_checks(build(rows, flat_fx()))


def test_checks_require_microsoft_from_fy2019():
    rows = [r for r in clean_rows() if not (r.company == "microsoft" and r.fiscal_year < 2021)]
    with pytest.raises(DataQualityError, match="FY2019"):
        run_checks(build(rows, flat_fx()))


def test_checks_flag_missing_fx():
    fx = {d: v for d, v in flat_fx().items() if d < date(2025, 1, 1)}
    with pytest.raises(ValueError, match="valid days"):
        build(clean_rows(), fx)
