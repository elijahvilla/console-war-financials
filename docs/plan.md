# Console War Financials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** an automated pipeline that pulls Microsoft and Sony annual SEC filings and extracts the gaming-segment numbers. It normalizes fiscal years and currency, checks data quality, and produces an Excel variance report, README charts, and a monthly refresh.

**Architecture:**
- `cwf/sec.py` fetches EDGAR JSON and XBRL instances politely, with a disk cache.
- `cwf/xbrl.py` turns an instance into flat `Fact`s, dimensions included.
- `cwf/extract.py` maps facts to tidy rows using `tag_map.yaml`.
- DuckDB loads the rows. SQL files de-duplicate restatements and build the analysis views. `checks.py` fails loudly.
- `report_xlsx.py` and `charts.py` render the outputs, and `pipeline.py` runs end to end.

**Tech Stack:** Python 3, requests, duckdb, openpyxl, matplotlib, pyyaml, pytest. XML parsing uses stdlib `xml.etree`.

**Spec:** `docs/design.md`. Read its **Spike findings**: they pin the real tag names.

**Repo:** `C:\Users\ual-laptop\Documents\Claude Work\console-war-financials\`. Its `.env` already exists, created by Elijah. Work on branch `build`.

## Global Constraints
- $0: SEC EDGAR plus FRED's keyless CSV (`https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXJPUS`, JPY per USD, daily). No API keys.
- User-Agent:
  - The value comes only from env var `SEC_USER_AGENT`, loaded from `.env` via python-dotenv.
  - It is never hard-coded, printed, logged, or written to cache files.
  - If it is missing, raise `ConfigError("set SEC_USER_AGENT in .env")`.
- Throttle: at least 0.2 s between SEC requests, i.e. no more than 5/s against SEC's limit of 10/s. Retry 429/5xx up to 3 times with backoff.
- Every output number carries `accession` and `concept`. No hand-typed figures anywhere in code or outputs.
- Never silently mix currencies or fiscal years:
  - Sony values are stored in JPY. USD values are separate derived columns.
  - Fiscal years are labeled `FY<year of period end>`.
- Tests run offline: fixtures only, no network in `pytest`.
- `.gitignore`: `.env`, `__pycache__/`, `.pytest_cache/`, `.superpowers/`, `data/cache/`, `*.duckdb`.
- Repo stays private until Elijah OKs public. Nothing goes on the resume until built and public.

## Review Focus
1. **The concept/axis changes across years** (GAAP→IFRS, `sne:`→`sony:`, Gaming→XBOX). Expect a continuous series with no gaps and no double counting. Test: `test_extract_handles_renamed_members` (Task 4).
2. **Restated years.** The same company, FY, and metric appear in 2–3 filings with different values. Expect the latest filing to win and the older values to go to the restatement log. Test: `test_dedup_latest_filing_wins_and_logs` (Task 6).
3. **Non-annual or instant contexts** (quarters inside a 10-K, balance-sheet instants). Expect only durations of 330–380 days to be used. Test: `test_extract_ignores_non_annual_periods` (Task 4).
4. **FX gaps** (FRED blanks `.` on holidays). Expect blanks to be skipped and the period average taken over valid days; fail if fewer than 200 valid days. Test: `test_fx_average_skips_blanks` (Task 5).
5. **YoY with a missing prior year, or a zero/negative base** (e.g. a negative operating income). Expect the YoY % to be empty, never a crash or a fake number. Commentary still renders. Test: `test_yoy_blank_when_no_prior_or_nonpositive_base` (Task 6).

---

### Task 1: Scaffold and SEC client

**Files:**
- Create:
  - `requirements.txt`, `.gitignore`, `.env.example` (`SEC_USER_AGENT=Your Name you@example.com`), `pytest.ini`
  - `cwf/__init__.py`, `cwf/sec.py`, `docs/design.md`
  - Fixtures under `tests/fixtures/`
- Test: `tests/test_sec.py`

**Interfaces (produces):**
- `class ConfigError(Exception)`
- `SecClient(user_agent: str | None = None, cache_dir: Path = Path("data/cache"), min_interval: float = 0.2, session=None)`
  - Reads env when `user_agent` is None.
- `SecClient.get(url: str) -> bytes`
  - Uses the disk cache keyed by `sha256(url)`. Cache files hold only the response body.
- `SecClient.get_json(url: str) -> dict`

- [ ] **Step 1: Write failing tests** with a fake session object that records calls:
  - `test_missing_user_agent_raises`
  - `test_user_agent_header_sent_but_not_cached`: the cache file bytes must not contain the UA string.
  - `test_cache_hit_skips_network`: a second `get` makes 0 extra session calls.
  - `test_throttle_spaces_requests`: inject a fake clock; two misses ⇒ a sleep of ≥ 0.2 s is requested.
  - `test_retries_on_429_then_succeeds`
- [ ] **Step 2:** Run `python -m pytest tests/test_sec.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3:** Implement `cwf/sec.py`.
- [ ] **Step 4:** Run `python -m pytest -q`. Expected: 5 passed.
- [ ] **Step 5:** Create the repo with `git init -b build` (not `main` yet). Then commit "Scaffold and polite SEC client".

### Task 2: XBRL instance parser

**Files:**
- Create: `cwf/xbrl.py`, `tests/fixtures/mini_instance.xml`
- Test: `tests/test_xbrl.py`

The fixture is a hand-written ~40-line instance. It has:
- one context without dimensions;
- one with two explicit members;
- one instant context;
- a `unit` of JPY;
- a nil fact.

**Interfaces (produces):**
- `Fact(concept: str, value: float | None, unit: str | None, start: date | None, end: date, dims: frozenset[tuple[str, str]], decimals: str | None)`
  - Concept, axis, and member names are **local names without prefixes**, e.g. `("SegmentsAxis", "GameAndNetworkServicesMember")`.
  - Non-numeric facts are dropped.
- `parse_instance(xml: bytes) -> list[Fact]`

- [ ] **Step 1: Write failing tests:**
  - `test_parses_dimensional_fact`
  - `test_instant_context_has_no_start`
  - `test_unit_resolved_to_currency_code` (gives `"JPY"`)
  - `test_nil_and_text_facts_dropped`
  - `test_prefix_stripped_from_members`
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement with `xml.etree.ElementTree`.
  - Build a context map: id → (start, end, dims).
  - Build a unit map: id → the local part of the measure.
  - Iterate the root's children that have `contextRef`.
- [ ] **Step 4:** Run `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5:** Commit "XBRL instance parser with dimensions".

### Task 3: Filing discovery

**Files:**
- Create: `cwf/filings.py`, `tests/fixtures/submissions_*.json`, `tests/fixtures/index_*.json`
- Test: `tests/test_filings.py`

**Interfaces (produces):**
- `COMPANIES = {"microsoft": ("0000789019", "10-K"), "sony": ("0000313838", "20-F")}`
- `Filing(company: str, accession: str, filing_date: date, report_date: date, instance_url: str)`
- `list_annual_filings(client: SecClient, company: str, since_report_year: int = 2015) -> list[Filing]`
  - Sorted by filing_date ascending.
  - Merges `filings.recent` with each page in `filings.files`, fetched from `https://data.sec.gov/submissions/<name>`.
  - Picks the instance from the archive's `index.json`: prefer `*_htm.xml`; else the `.xml` that isn't `_cal/_def/_lab/_pre` and isn't `FilingSummary.xml`.
  - Excludes amendments (`10-K/A`, `20-F/A`). Amendments are ruled out of scope.

- [ ] **Step 1: Write failing tests:**
  - `test_merges_recent_and_paged_files`
  - `test_picks_inline_instance`
  - `test_picks_legacy_instance_ignoring_linkbases` (index lists `sne-20180331.xml`, `sne-20180331_cal.xml`, `FilingSummary.xml` → picks the first)
  - `test_excludes_amendments`
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: all pass.
- [ ] **Step 5:** Commit "Filing discovery for 10-K and 20-F".

### Task 4: Tag map and extraction (includes a live enumeration step)

**Files:**
- Create:
  - `cwf/tag_map.yaml`, `cwf/extract.py`
  - `cwf/explore.py`: a dev tool that prints every G&NS/Gaming dimensional fact across all filings
- Test: `tests/test_extract.py`

**Interfaces:**
- Consumes: `Fact`, `Filing`.
- Produces:
  - `Row(company, fiscal_year: int, period_start: date, period_end: date, metric: str, value: float, currency: str, accession: str, filing_date: date, concept: str, basis: str)`
    - `basis` is `"us-gaap"` or `"ifrs"`, from the concept's namespace family. The parser records it via the concept-to-basis lookup in the tag map.
  - `extract(filing: Filing, facts: list[Fact]) -> list[Row]`
- Metrics:
  - Microsoft: `revenue`.
  - Sony:
    - `revenue`: total incl. intersegment, i.e. `OperatingSegmentsMember` and no sales-channel member.
    - `revenue_external`
    - `operating_income`
    - product buckets: `rev_hardware`, `rev_digital_software`, `rev_network_services`, `rev_other`. These are external, per the tag map.

`tag_map.yaml` shape (exact keys):
```yaml
microsoft:
  revenue: {concepts: [RevenueFromContractWithCustomerExcludingAssessedTax], require: {ProductOrServiceAxis: [GamingMember, XBOXMember]}, exactly_dims: 1}
sony:
  revenue: {concepts: [Revenues, Revenue], require: {StatementBusinessSegmentsAxis|SegmentsAxis: [GameAndNetworkServicesMember], ConsolidationItemsAxis|SegmentConsolidationItemsAxis: [OperatingSegmentsMember]}, exactly_dims: 2}
  # ...operating_income, revenue_external, and product buckets filled from Step 1's enumeration
basis: {Revenues: us-gaap, OperatingIncomeLoss: us-gaap, RevenueFromContractWithCustomerExcludingAssessedTax: us-gaap, Revenue: ifrs, ProfitLossFromOperatingActivities: ifrs}
```
A rule matches a fact only if:
- the concept is in `concepts`;
- every required axis (any alias split on `|`) has one of the listed members;
- the fact has exactly `exactly_dims` dimensions.

Exact dimension counts stop the GAAP-era Sony `Revenues` fact with only `StatementBusinessSegmentsAxis` from double counting against the `OperatingSegmentsMember` one.

- [ ] **Step 1 (live, needs `.env`):** Implement `explore.py` (no test: it's a dev tool) and run `python -m cwf.explore sony`.
  - Freeze every G&NS product-axis member into one of the 4 buckets.
  - Then run `python -m cwf.explore microsoft` and confirm only Gaming/XBOX members exist.
  - Paste the member→bucket table into the ledger as a `Ruling:` line, listing the source filing for each member.
- [ ] **Step 2: Write failing tests** against small synthetic `Fact` lists:
  - `test_extract_handles_renamed_members`: GamingMember FY2023 + XBOXMember FY2024 → 2 revenue rows.
  - `test_extract_ignores_non_annual_periods`: a 91-day fact and an instant are dropped.
  - `test_exact_dim_count_prevents_double_count`
  - `test_basis_from_concept`
  - `test_fiscal_year_is_period_end_year`: Sony 2025-04-01→2026-03-31 ⇒ 2026.
- [ ] **Step 3:** Run. Expected: FAIL.
- [ ] **Step 4:** Implement `extract.py`.
- [ ] **Step 5:** Run. Expected: all pass.
- [ ] **Step 6:** Commit "Tag map and gaming-segment extraction".

### Task 5: FX rates

**Files:**
- Create: `cwf/fx.py`, `tests/fixtures/dexjpus_sample.csv`
- Test: `tests/test_fx.py`

**Interfaces (produces):**
- `load_dexjpus(client_get: Callable[[str], bytes]) -> dict[date, float]`
  - Skips `.` and blanks.
  - The FRED request goes through a plain `requests` call. It needs no UA secret, but it still goes through the disk cache.
- `period_average(rates: dict[date, float], start: date, end: date) -> float`
  - Raises `ValueError` if there are fewer than 200 valid days.

- [ ] **Step 1: Write failing tests:**
  - `test_fx_average_skips_blanks`
  - `test_fx_raises_on_sparse_period`
  - `test_fx_parses_fred_header` (columns `observation_date,DEXJPUS`; also accept the older `DATE,DEXJPUS`)
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: all pass.
- [ ] **Step 5:** Commit "FRED USD/JPY period averages".

### Task 6: DuckDB model, de-duplication, analysis views, quality checks

**Files:**
- Create:
  - `cwf/db.py`, `cwf/checks.py`
  - `sql/01_segment_year.sql`, `sql/02_restatements.sql`, `sql/03_analysis.sql`
- Test: `tests/test_db.py`, `tests/test_checks.py`

**Interfaces:**
- Consumes: `Row`, `period_average`.
- Produces:
  - `build(rows: list[Row], fx: dict[date, float], db_path: str = ":memory:") -> duckdb.DuckDBPyConnection`
    - Loads the `raw_rows` and `fx_period` tables (one avg rate per Sony period), then runs `sql/*.sql` in order.
  - `segment_year`: company, fiscal_year, metric, value, currency, value_usd, accession, concept, basis.
    - The latest `filing_date` wins per (company, fiscal_year, metric).
  - `restatements`: superseded values, with old/new accession, the delta, and `basis_change` (bool).
  - `v_yoy`: per company/metric/fy:
    - value, prior, yoy_abs, yoy_pct;
    - for Sony, also yoy_pct in JPY and in USD.
    - yoy_pct is NULL if there is no prior year or the prior value is ≤ 0.
  - `v_sony_mix`: bucket share of `revenue_external`.
  - `v_sony_margin`: operating_income / revenue.
  - `v_head_to_head`: revenue in USD for both companies by fiscal year, with each company's share of the combined total.
- `run_checks(con) -> None` raises `DataQualityError(list[str])` when any check fails:
  - (a) Sony bucket sum is within 0.5% of `revenue_external` each year.
  - (b) No gaps in fiscal years per company/metric between its min and max.
  - (c) Microsoft FY2019 through its latest year is present.
  - (d) Exactly one row per key in `segment_year`.

- [ ] **Step 1: Write failing tests:**
  - `test_dedup_latest_filing_wins_and_logs`: FY2020 Sony operating income ¥342.192bn (GAAP, 2021 filing) and ¥341.718bn (IFRS, 2023 filing). Expect the IFRS value to win and one restatement with `basis_change=True`.
  - `test_yoy_blank_when_no_prior_or_nonpositive_base`
  - `test_usd_conversion_uses_period_average`
  - `test_checks_flag_bucket_mismatch`
  - `test_checks_flag_year_gap`
  - `test_checks_pass_on_clean_fixture`
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. The SQL lives in `sql/`, not in Python strings.
- [ ] **Step 4:** Run. Expected: all pass.
- [ ] **Step 5:** Commit "DuckDB model, restatement log, and data-quality checks".

### Task 7: Excel variance report and charts

**Files:**
- Create: `cwf/commentary.py`, `cwf/report_xlsx.py`, `cwf/charts.py`
- Test: `tests/test_commentary.py`, `tests/test_report.py`

**Interfaces (produces):**
- `commentary(company: str, fy: int, yoy: dict, mix: dict | None, events: dict[int, str]) -> str`
  - Rule-based, one sentence.
  - Names the biggest-moving bucket for Sony.
  - Appends the event note from `EVENTS = {("microsoft", 2024): "first full year including Activision Blizzard (closed Oct 2023)"}`.
  - Notes the FX effect when JPY and USD growth differ by more than 5 points.
- `write_report(con, path: Path) -> None` writes these tabs:
  - `Summary`: head-to-head USD by FY plus share.
  - `Xbox`, `PlayStation`: value, prior, YoY $, YoY %, plus Sony's JPY/USD columns and commentary.
  - `Restatements`.
  - `Sources`: every number's accession, concept, and basis.
  - Formatting: frozen header rows, number formats (`#,##0` in millions, `0.0%`), red/green conditional fill on YoY %, and column widths.
- `write_charts(con, out_dir: Path) -> list[Path]`, three PNGs:
  - `revenue_usd.png`
  - `sony_mix.png`
  - `sony_margin.png`
  - Every chart has a source footnote "Source: SEC EDGAR 10-K/20-F XBRL".
  - Use the `dataviz` skill guidance for colors (Xbox green / PlayStation blue are OK as brand-meaning colors).

- [ ] **Step 1: Write failing tests:**
  - `test_commentary_names_top_bucket`
  - `test_commentary_appends_event`
  - `test_commentary_flags_fx_effect`
  - `test_report_has_expected_sheets_and_sources` (open with openpyxl; Sources rows = segment_year rows)
  - `test_charts_written` (3 files exist, non-empty; matplotlib `Agg` backend)
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: all pass.
- [ ] **Step 5:** Commit "Excel variance report, commentary, charts".

### Task 8: Pipeline, live run, automation, README, private repo

**Files:**
- Create:
  - `cwf/pipeline.py`
  - `.github/workflows/refresh.yml`
  - `README.md`
  - `reports/console_war_financials.xlsx` and `docs/*.png` (generated)
- Test: `tests/test_pipeline.py`

**Interfaces (produces):** `python -m cwf.pipeline [--offline]`.
- It runs discovery → parse → extract → FX → build → checks → report → charts.
- `--offline` uses only the cache and fails on a miss.
- It prints a short summary (filings used, rows, restatements, checks passed) and never the UA.

- [ ] **Step 1: Write failing test** `test_pipeline_offline_end_to_end`: a fixture cache dir with 2 tiny filings per company plus an FX sample → the report and charts get written, and the checks pass.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: all pass.
- [ ] **Step 5 (live):**
  - Run `python -m cwf.pipeline`, then `python -m cwf.pipeline --offline`, and confirm identical outputs.
  - Cross-check 3 numbers by hand against the spike table in the spec: MSFT FY2021 = 15.370bn, Sony FY2026 G&NS revenue = ¥4,685.651bn, Sony FY2024 G&NS OI = ¥290.184bn.
  - If `run_checks` fails, fix the cause (usually the tag map). Never loosen a check without a ledgered ruling.
- [ ] **Step 6:** Write `refresh.yml`:
  - Triggers: monthly cron `0 12 3 * *` plus `workflow_dispatch`.
  - Python setup, `pip install -r requirements.txt`, then `python -m cwf.pipeline` with `SEC_USER_AGENT: ${{ secrets.SEC_USER_AGENT }}`.
  - Commits `reports/` and `docs/*.png` if they changed. Permission: `contents: write`.
- [ ] **Step 7:** Write the README. Lead with the head-to-head chart and 3 findings with real numbers from the outputs. Then cover:
  - the question;
  - the sources;
  - the method: the tag changes, the GAAP→IFRS switch, the FX treatment, the restatement rule;
  - limitations: Microsoft doesn't disclose gaming profit, so the margin comparison is Sony-only; fiscal-year offset; annual only;
  - how to run it;
  - a short "not investment advice" line.
- [ ] **Step 8:** Run `python -m pytest -q` (all pass, offline) and commit "Pipeline, refresh workflow, README, results".
- [ ] **Step 9:** Run `gh repo create console-war-financials --private --source . --push`, set the default branch to `build`, and tell Elijah to add the `SEC_USER_AGENT` repo secret himself:
  ```
  ! gh secret set SEC_USER_AGENT -R elijahvilla/console-war-financials
  ```
  It prompts for the value. Send him the link and **wait for his OK** to go public. After the OK:
  - Make the repo public.
  - Add the project to `JOB_HUNT/profile/master_profile.yaml` as `status: built`, with `repo_url` and bullets that use real output numbers.
  - Run `python -m pytest tests/test_profile.py`.
