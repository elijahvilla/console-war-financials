"""Data-quality checks. Any failure stops the pipeline with every problem listed."""

BUCKETS = ("rev_digital_software", "rev_network_services", "rev_hardware_other")
TOLERANCE = 0.005
MICROSOFT_FIRST_FY = 2019


class DataQualityError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("data-quality checks failed:\n- " + "\n- ".join(problems))


def run_checks(con) -> None:
    problems = []

    # (a) Sony's product buckets add up to its sales to outside customers.
    for fy, n, total, external in con.execute(f"""
        SELECT e.fiscal_year, count(b.metric), sum(b.value), any_value(e.value)
        FROM segment_year e
        LEFT JOIN segment_year b ON b.company = 'sony' AND b.fiscal_year = e.fiscal_year
                                AND b.metric IN {BUCKETS}
        WHERE e.company = 'sony' AND e.metric = 'revenue_external'
        GROUP BY e.fiscal_year ORDER BY 1""").fetchall():
        if n == 0:
            continue  # years before the product split was reported
        if n != len(BUCKETS):
            problems.append(f"sony FY{fy}: only {n} of {len(BUCKETS)} product buckets")
        elif abs(total / external - 1) > TOLERANCE:
            problems.append(f"sony FY{fy}: product bucket sum {total:,.0f} vs external revenue {external:,.0f}")

    # (b) No missing years inside each series.
    for company, metric, years in con.execute("""
        SELECT company, metric, list(fiscal_year ORDER BY fiscal_year) FROM segment_year GROUP BY 1, 2""").fetchall():
        missing = sorted(set(range(min(years), max(years) + 1)) - set(years))
        if missing:
            problems.append(f"{company} {metric}: year gap, missing FY{', FY'.join(map(str, missing))}")

    # (c) Xbox history covers at least FY2019 onward.
    ms_years = {y for (y,) in con.execute(
        "SELECT fiscal_year FROM segment_year WHERE company = 'microsoft' AND metric = 'revenue'").fetchall()}
    if not ms_years or min(ms_years) > MICROSOFT_FIRST_FY:
        problems.append(f"microsoft revenue must start by FY{MICROSOFT_FIRST_FY} (got FY{min(ms_years, default=0)})")

    # (d) One value per key: the winning filing must not report two different numbers for the same thing.
    for company, fy, metric, values in con.execute("""
        SELECT r.company, r.fiscal_year, r.metric, list(DISTINCT r.value)
        FROM raw_rows r JOIN segment_year s
          ON s.company = r.company AND s.fiscal_year = r.fiscal_year AND s.metric = r.metric
         AND s.accession = r.accession
        GROUP BY 1, 2, 3 HAVING count(DISTINCT r.value) > 1""").fetchall():
        problems.append(f"{company} FY{fy} {metric}: conflict inside one filing, values {values}")
    dupes = con.execute("""SELECT count(*) FROM (SELECT 1 FROM segment_year
                           GROUP BY company, fiscal_year, metric HAVING count(*) > 1)""").fetchone()[0]
    if dupes:
        problems.append(f"segment_year has {dupes} duplicate keys")

    # (e) Every number has a USD value.
    no_usd = con.execute("SELECT count(*) FROM segment_year WHERE value_usd IS NULL").fetchone()[0]
    if no_usd:
        problems.append(f"{no_usd} rows have no USD value (missing FX period)")

    if problems:
        raise DataQualityError(problems)
