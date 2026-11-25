import openpyxl

from cwf.charts import write_charts
from cwf.db import build
from cwf.report_xlsx import write_report
from tests.helpers import clean_sony_year, flat_fx, ms


def model():
    rows = [ms(fy, (10 + fy - 2024) * 1e9) for fy in range(2019, 2027)]
    rows += [r for fy in range(2019, 2027) for r in clean_sony_year(fy, scale=1e9 * (1 + (fy - 2019) / 10))]
    return build(rows, flat_fx())


def test_report_has_expected_sheets_and_sources(tmp_path):
    con = model()
    path = tmp_path / "r.xlsx"
    write_report(con, path)
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["Summary", "Xbox", "PlayStation", "Restatements", "Sources"]
    n_rows = con.execute("select count(*) from segment_year").fetchone()[0]
    assert wb["Sources"].max_row - 1 == n_rows
    assert wb["Summary"].freeze_panes == "A2"
    headers = [c.value for c in wb["PlayStation"][1]]
    assert "YoY % (JPY)" in headers and "YoY % (USD)" in headers and "Commentary" in headers


def test_charts_written(tmp_path):
    paths = write_charts(model(), tmp_path)
    assert sorted(p.name for p in paths) == ["revenue_usd.png", "sony_margin.png", "sony_mix.png"]
    assert all(p.stat().st_size > 5000 for p in paths)
