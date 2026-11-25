-- One value per company / fiscal year / metric: the most recent filing wins (restated numbers replace old ones).
-- USD value: Microsoft reports in USD; Sony's yen are divided by the fiscal-year average JPY-per-USD rate.
CREATE OR REPLACE TABLE segment_year AS
WITH ranked AS (
    SELECT r.*,
           row_number() OVER (PARTITION BY company, fiscal_year, metric
                              ORDER BY filing_date DESC, accession DESC, concept) AS rk
    FROM raw_rows r
)
SELECT r.company, r.fiscal_year, r.period_start, r.period_end, r.metric, r.value, r.currency,
       CASE WHEN r.currency = 'USD' THEN r.value ELSE r.value / f.jpy_per_usd END AS value_usd,
       f.jpy_per_usd,
       r.accession, r.filing_date, r.concept, r.basis
FROM ranked r
LEFT JOIN fx_period f
       ON r.currency = 'JPY' AND f.period_start = r.period_start AND f.period_end = r.period_end
WHERE r.rk = 1;
