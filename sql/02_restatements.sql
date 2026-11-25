-- Every older filing whose value for the same company / year / metric differs from the winning value.
-- basis_change = the restatement came with an accounting-standard switch (US GAAP -> IFRS for Sony, FY2021).
CREATE OR REPLACE TABLE restatements AS
WITH older AS (
    SELECT DISTINCT company, fiscal_year, metric, value, accession, filing_date, basis
    FROM raw_rows
)
SELECT s.company, s.fiscal_year, s.metric,
       o.value      AS old_value,
       o.accession  AS old_accession,
       o.basis      AS old_basis,
       s.value      AS new_value,
       s.accession  AS new_accession,
       s.basis      AS new_basis,
       s.value - o.value AS delta,
       o.basis <> s.basis AS basis_change
FROM segment_year s
JOIN older o USING (company, fiscal_year, metric)
WHERE o.filing_date < s.filing_date AND o.value <> s.value
ORDER BY s.company, s.metric, s.fiscal_year, o.filing_date;
