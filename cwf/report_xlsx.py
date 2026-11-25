"""Excel variance report: Summary, Xbox, PlayStation, Restatements, Sources (every number traced to its filing)."""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from cwf.commentary import EVENTS, commentary
from cwf.filings import COMPANIES

HEADER_FILL = PatternFill("solid", fgColor="1F2937")
HEADER_FONT = Font(bold=True, color="FFFFFF")
GOOD_FILL = PatternFill("solid", fgColor="D9F2E3")
BAD_FILL = PatternFill("solid", fgColor="F9DEDC")
MILLIONS = "#,##0"
PCT = "0.0%"
M = 1e6


def _sheet(wb, title, headers, rows, formats=None, pct_cols=(), widths=None):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for cell in ws[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for r in rows:
        ws.append(list(r))
    ws.freeze_panes = "A2"
    last = ws.max_row
    for idx, fmt in (formats or {}).items():
        col = get_column_letter(idx + 1)
        for c in ws[f"{col}2:{col}{max(last, 2)}"]:
            c[0].number_format = fmt
    for idx in pct_cols:
        rng = f"{get_column_letter(idx + 1)}2:{get_column_letter(idx + 1)}{max(last, 2)}"
        ws.conditional_formatting.add(rng, CellIsRule(operator="greaterThan", formula=["0"], fill=GOOD_FILL))
        ws.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0"], fill=BAD_FILL))
    for i, h in enumerate(headers):
        ws.column_dimensions[get_column_letter(i + 1)].width = (widths or {}).get(i, max(12, min(len(h) + 2, 22)))
    ws.row_dimensions[1].height = 32
    return ws


def _yoy(con, company):
    out = {}
    for metric, fy, value, prior, yoy_abs, pct, value_usd, pct_usd in con.execute("""
        SELECT metric, fiscal_year, value, prior, yoy_abs, yoy_pct, value_usd, yoy_pct_usd
        FROM v_yoy WHERE company = ?""", [company]).fetchall():
        out.setdefault(fy, {})[metric] = dict(value=value, prior=prior, yoy_abs=yoy_abs, yoy_pct=pct,
                                              value_usd=value_usd, yoy_pct_usd=pct_usd)
    return out


def write_report(con, path: Path) -> None:
    wb = Workbook()
    wb.remove(wb.active)

    h2h = con.execute("SELECT fiscal_year, xbox_usd, playstation_usd, xbox_share, playstation_share FROM v_head_to_head").fetchall()
    ms, sony = _yoy(con, "microsoft"), _yoy(con, "sony")
    summary = [(fy, x / M, p / M, xs, ps, ms[fy]["revenue"]["yoy_pct_usd"], sony[fy]["revenue"]["yoy_pct_usd"])
               for fy, x, p, xs, ps in h2h]
    ws = _sheet(wb, "Summary", ["Fiscal year", "Xbox gaming revenue ($M)", "PlayStation G&NS revenue ($M)",
                                "Xbox share", "PlayStation share", "Xbox YoY % (USD)", "PlayStation YoY % (USD)"],
                summary, {1: MILLIONS, 2: MILLIONS, 3: PCT, 4: PCT, 5: PCT, 6: PCT}, pct_cols=(5, 6))
    ws.append([])
    for note in ["Fiscal years: Microsoft ends June 30, Sony ends March 31 (labels use the year the period ends).",
                 "Sony is reported in yen; USD = yen / fiscal-year average JPY per USD (FRED DEXJPUS).",
                 "Microsoft does not disclose gaming operating income, so margins are PlayStation-only.",
                 "Source: SEC EDGAR 10-K (Microsoft) and 20-F (Sony) XBRL. Not investment advice."]:
        ws.append([note])

    xbox_rows = []
    for fy in sorted(ms):
        r = ms[fy]["revenue"]
        xbox_rows.append((fy, r["value"] / M, r["prior"] / M if r["prior"] else None,
                          r["yoy_abs"] / M if r["yoy_abs"] is not None else None, r["yoy_pct"],
                          commentary("microsoft", fy, ms[fy], None, EVENTS)))
    _sheet(wb, "Xbox", ["Fiscal year", "Gaming revenue ($M)", "Prior year ($M)", "YoY $ ($M)", "YoY %", "Commentary"],
           xbox_rows, {1: MILLIONS, 2: MILLIONS, 3: MILLIONS, 4: PCT}, pct_cols=(4,), widths={5: 90})

    fx = dict(con.execute("SELECT fiscal_year, jpy_per_usd FROM segment_year WHERE company='sony' AND metric='revenue'").fetchall())
    ps_rows = []
    for fy in sorted(sony):
        y = sony[fy]
        r, oi = y["revenue"], y.get("operating_income", {})
        buckets = {k: y[k] for k in ("rev_digital_software", "rev_network_services", "rev_hardware_other") if k in y}
        mix_change = {k: v["yoy_abs"] for k, v in buckets.items() if v["yoy_abs"] is not None} or None
        margin = oi["value"] / r["value"] if oi else None
        ps_rows.append((fy, r["value"] / M, r["prior"] / M if r["prior"] else None,
                        r["yoy_abs"] / M if r["yoy_abs"] is not None else None, r["yoy_pct"],
                        r["value_usd"] / M, r["yoy_pct_usd"], fx.get(fy),
                        oi["value"] / M if oi else None, margin,
                        *[(buckets[k]["value"] / M if k in buckets else None)
                          for k in ("rev_digital_software", "rev_network_services", "rev_hardware_other")],
                        commentary("sony", fy, y, mix_change, EVENTS)))
    _sheet(wb, "PlayStation", ["Fiscal year", "G&NS revenue (¥M)", "Prior year (¥M)", "YoY ¥ (¥M)", "YoY % (JPY)",
                               "G&NS revenue ($M)", "YoY % (USD)", "JPY per USD (FY avg)", "Operating income (¥M)",
                               "Operating margin", "Digital software & add-ons (¥M)", "Network services (¥M)",
                               "Hardware & others (¥M)", "Commentary"],
           ps_rows, {1: MILLIONS, 2: MILLIONS, 3: MILLIONS, 4: PCT, 5: MILLIONS, 6: PCT, 7: "0.00", 8: MILLIONS,
                     9: PCT, 10: MILLIONS, 11: MILLIONS, 12: MILLIONS}, pct_cols=(4, 6), widths={13: 110})

    rest = con.execute("""SELECT company, metric, fiscal_year, old_value / 1e6, old_accession, old_basis,
                          new_value / 1e6, new_accession, new_basis, delta / 1e6, basis_change FROM restatements""").fetchall()
    _sheet(wb, "Restatements", ["Company", "Metric", "Fiscal year", "Old value (M)", "Old filing", "Old basis",
                                "New value (M)", "New filing", "New basis", "Change (M)", "Accounting-basis change"],
           rest, {3: MILLIONS, 6: MILLIONS, 9: MILLIONS})

    src = []
    for company, fy, metric, value, currency, concept, basis, acc, filed in con.execute("""
        SELECT company, fiscal_year, metric, value, currency, concept, basis, accession, filing_date
        FROM segment_year ORDER BY company, metric, fiscal_year""").fetchall():
        cik = int(COMPANIES[company][0])
        src.append((company, fy, metric, value, currency, concept, basis, acc, filed,
                    f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/"))
    _sheet(wb, "Sources", ["Company", "Fiscal year", "Metric", "Value", "Currency", "XBRL concept", "Basis",
                           "Accession", "Filing date", "Filing (EDGAR)"],
           src, {3: "#,##0", 8: "yyyy-mm-dd"}, widths={5: 48, 9: 60})

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
