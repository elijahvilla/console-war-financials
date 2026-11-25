from datetime import date

import pytest

from cwf.db import build
from tests.helpers import GAAP, IFRS, clean_sony_year, flat_fx, ms, sony


def q(con, sql):
    return con.execute(sql).fetchall()


def test_dedup_latest_filing_wins_and_logs():
    rows = [
        sony(2021, "operating_income", 342.192e9, filed=date(2021, 6, 22), acc="A2021", basis=GAAP,
             concept="OperatingIncomeLoss"),
        sony(2021, "operating_income", 341.718e9, filed=date(2023, 6, 20), acc="A2023", basis=IFRS,
             concept="ProfitLossFromOperatingActivities"),
        sony(2021, "operating_income", 341.718e9, filed=date(2022, 6, 28), acc="A2022", basis=IFRS,
             concept="ProfitLossFromOperatingActivities"),
    ]
    con = build(rows, flat_fx())
    assert q(con, "select value, accession, basis from segment_year") == [(341.718e9, "A2023", IFRS)]
    rs = q(con, "select old_value, old_accession, new_accession, basis_change from restatements")
    assert rs == [(342.192e9, "A2021", "A2023", True)]


def test_yoy_blank_when_no_prior_or_nonpositive_base():
    rows = [sony(2014, "operating_income", -18.8e9), sony(2015, "operating_income", 48.1e9),
            sony(2016, "operating_income", 88.7e9), ms(2020, 11.575e9)]
    con = build(rows, flat_fx())
    got = dict(q(con, "select company || fiscal_year, yoy_pct from v_yoy where metric in ('operating_income','revenue')"))
    assert got["sony2014"] is None  # no prior year
    assert got["sony2015"] is None  # prior year was a loss
    assert got["sony2016"] == pytest.approx(88.7 / 48.1 - 1)
    assert got["microsoft2020"] is None


def test_usd_conversion_uses_period_average():
    fx = flat_fx(100.0)
    fx.update({d: 200.0 for d in fx if date(2025, 4, 1) <= d <= date(2025, 9, 30)})
    con = build([sony(2026, "revenue", 3000.0), ms(2026, 21.79e9)], fx)
    usd = dict(q(con, "select company, value_usd from segment_year"))
    assert usd["microsoft"] == 21.79e9
    avg = q(con, "select jpy_per_usd from segment_year where company='sony'")[0][0]
    assert 140 < avg < 160 and usd["sony"] == pytest.approx(3000.0 / avg)


def test_head_to_head_only_years_both_report():
    rows = [ms(2025, 23.455e9), ms(2026, 21.79e9)] + clean_sony_year(2026, scale=1e9) + clean_sony_year(2024, scale=1e9)
    con = build(rows, flat_fx(150.0))
    got = q(con, "select fiscal_year, xbox_usd, playstation_usd, round(xbox_share, 4) from v_head_to_head")
    assert got == [(2026, 21.79e9, pytest.approx(1000e9 / 150), round(21.79e9 / (21.79e9 + 1000e9 / 150), 4))]


def test_mix_and_margin_views():
    con = build(clean_sony_year(2026), flat_fx())
    mix = dict(q(con, "select bucket, share from v_sony_mix"))
    assert mix == {"rev_digital_software": pytest.approx(500 / 900), "rev_network_services": pytest.approx(150 / 900),
                   "rev_hardware_other": pytest.approx(250 / 900)}
    assert q(con, "select margin from v_sony_margin") == [(pytest.approx(0.1),)]
