-- Year-over-year change. Growth % is left NULL when there is no prior year or the prior value is zero or a loss
-- (a % change off a negative base is meaningless). For Sony, growth is shown in yen and in USD side by side.
CREATE OR REPLACE VIEW v_yoy AS
SELECT c.company, c.metric, c.fiscal_year, c.currency,
       c.value,
       p.value                                   AS prior,
       c.value - p.value                         AS yoy_abs,
       CASE WHEN p.value > 0 THEN c.value / p.value - 1 END         AS yoy_pct,
       c.value_usd,
       p.value_usd                               AS prior_usd,
       CASE WHEN p.value_usd > 0 THEN c.value_usd / p.value_usd - 1 END AS yoy_pct_usd
FROM segment_year c
LEFT JOIN segment_year p
       ON p.company = c.company AND p.metric = c.metric AND p.fiscal_year = c.fiscal_year - 1;

-- PlayStation revenue mix: each product bucket as a share of sales to outside customers.
CREATE OR REPLACE VIEW v_sony_mix AS
SELECT b.fiscal_year, b.metric AS bucket, b.value, b.value_usd, b.value / e.value AS share
FROM segment_year b
JOIN segment_year e
  ON e.company = 'sony' AND e.metric = 'revenue_external' AND e.fiscal_year = b.fiscal_year
WHERE b.company = 'sony' AND b.metric LIKE 'rev\_%' ESCAPE '\';

-- PlayStation operating margin (Microsoft does not disclose gaming profit, so there is no Xbox equivalent).
CREATE OR REPLACE VIEW v_sony_margin AS
SELECT o.fiscal_year, o.value AS operating_income, r.value AS revenue, o.value / r.value AS margin
FROM segment_year o
JOIN segment_year r ON r.company = 'sony' AND r.metric = 'revenue' AND r.fiscal_year = o.fiscal_year
WHERE o.company = 'sony' AND o.metric = 'operating_income';

-- Head to head in USD, years both companies report. Fiscal years differ: Microsoft ends June, Sony ends March.
CREATE OR REPLACE VIEW v_head_to_head AS
SELECT x.fiscal_year,
       x.value_usd AS xbox_usd,
       p.value_usd AS playstation_usd,
       x.value_usd / (x.value_usd + p.value_usd) AS xbox_share,
       p.value_usd / (x.value_usd + p.value_usd) AS playstation_share
FROM segment_year x
JOIN segment_year p ON p.company = 'sony' AND p.metric = 'revenue' AND p.fiscal_year = x.fiscal_year
WHERE x.company = 'microsoft' AND x.metric = 'revenue'
ORDER BY x.fiscal_year;
