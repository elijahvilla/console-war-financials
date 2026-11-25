"""Load extracted rows into DuckDB and build the model with the SQL files in sql/ (run in name order)."""
from datetime import date
from pathlib import Path

import duckdb

from cwf.fx import period_average

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
ROW_COLS = ["company", "fiscal_year", "period_start", "period_end", "metric", "value", "currency",
            "accession", "filing_date", "concept", "basis"]


def build(rows, fx: dict[date, float], db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(db_path)
    con.execute("""CREATE OR REPLACE TABLE raw_rows (company VARCHAR, fiscal_year INTEGER, period_start DATE,
                   period_end DATE, metric VARCHAR, value DOUBLE, currency VARCHAR, accession VARCHAR,
                   filing_date DATE, concept VARCHAR, basis VARCHAR)""")
    con.executemany(f"INSERT INTO raw_rows VALUES ({', '.join('?' * len(ROW_COLS))})",
                    [[getattr(r, c) for c in ROW_COLS] for r in rows])
    periods = sorted({(r.period_start, r.period_end) for r in rows if r.currency == "JPY"})
    con.execute("CREATE OR REPLACE TABLE fx_period (period_start DATE, period_end DATE, jpy_per_usd DOUBLE)")
    con.executemany("INSERT INTO fx_period VALUES (?, ?, ?)",
                    [(s, e, period_average(fx, s, e)) for s, e in periods])
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        con.execute(sql_file.read_text(encoding="utf-8"))
    return con
