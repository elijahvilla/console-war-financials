# Console War Financials: Design

**Status:** draft for Elijah's approval. **Date:** 2026-11-25. **Repo (to create):** `C:\Users\ual-laptop\Documents\Claude Work\console-war-financials\` (private GitHub first).

## Intent and why
Elijah wants a third portfolio repo that reads as **finance/analyst work** (for the Amazon AFRP, Vanguard, and other rotational-program roles), not just another data project. He chose to frame it around a company he cares about. Riot is private, so the frame is **Xbox vs PlayStation**: the console war told through each parent company's official SEC filings.

The interview story: "I built an automated pipeline that pulls Microsoft's and Sony's SEC filings, isolates the gaming segments, normalizes currencies and fiscal years, and produces a variance report like a finance team would."

## Goals
1. **Automated ingestion** from SEC EDGAR. No manual downloads and no API key.
   - Microsoft (CIK 789019): 10-K annual reports.
   - Sony Group (CIK 313838): 20-F annual reports.
2. **Extract gaming-segment numbers**, from the segment and revenue-breakdown tables in each filing's XBRL:
   - Microsoft: Gaming revenue only. The spike showed XBRL has no hardware/content split and no gaming operating income.
   - Sony: Game & Network Services (G&NS) revenue and operating income, plus its product split. All of this is confirmed in XBRL (see Spike findings).
3. **Normalize** so the comparison is fair:
   - **Fiscal years.** Microsoft's FY ends in June and Sony's ends in March. Each year is labeled with its period end, and the report states the offset.
   - **Currency.** Sony reports in yen, so its figures are converted to USD at the fiscal-year average USD/JPY rate (Federal Reserve series via FRED's keyless CSV). Growth is shown in **local currency and USD** side by side, so the effect of the exchange rate is visible.
4. **A SQL model layer** in DuckDB: raw facts → a clean `segment_year` fact table → analysis views (YoY growth, margin, mix, share of the combined total).
5. **Data-quality checks that fail loudly**:
   - Segment pieces sum to the segment total within a rounding tolerance.
   - No missing years in the covered range.
   - Each reported number has exactly one value per period after de-duplicating restatements (the latest filing wins, and the restatement is logged).
6. **An Excel variance report** (`reports/console_war_financials.xlsx`), formatted the way a finance team would expect:
   - A summary tab and a tab per company.
   - YoY $ and % variance columns.
   - Auto-written one-line commentary per year (rule-based, e.g. "Gaming revenue +16% YoY, driven by content & services; first full year including Activision").
7. **README charts** (matplotlib PNGs) and a README a recruiter can skim in 60 seconds: the question, the sources, the method, 3 real findings with numbers, and how to run it.
8. **Monthly GitHub Actions workflow** that checks for new filings, rebuilds, and commits updated outputs.

## Non-goals
- Sony quarterly data. It lives in 6-K press releases, not XBRL, and scraping it is fragile. Noted as a future step.
- Nintendo. It doesn't file with the SEC. Noted as a future step.
- Stock prices, valuation, or forecasting. This is reported fundamentals only.
- Investment advice of any kind. The README frames it as an analysis of reported segment results.

## Anti-goals (failure even if it "works")
- Any number that doesn't trace back to a specific filing (accession number and tag).
- Hard-coded figures typed in from articles.
- Mixing fiscal years or currencies silently.
- A README that overclaims, e.g. calling Microsoft Gaming "Xbox profit" when Microsoft doesn't disclose gaming operating income.

## Constraints
- $0: SEC EDGAR and FRED's keyless CSV only.
- SEC fair-access rules:
  - Every request carries a User-Agent with a contact. The value is set by Elijah as the env var `SEC_USER_AGENT` (a GitHub secret in Actions). It is never hard-coded or committed.
  - No more than 10 requests per second (the client throttles to about 5).
  - Raw filings are cached on disk.
- Python 3, with `requests`, `duckdb`, `openpyxl`, `matplotlib`, `pytest`, and an XML parser (stdlib `xml.etree`, or `lxml` if needed).
- Tests run offline from small fixture XBRL snippets.
- Repo private until Elijah OKs public. Goes on the resume only once built and public.

## Approaches considered
1. **Parse each filing's XBRL instance, including dimensional (segment) facts.** **Chosen.** It is the only reliable source of segment numbers, and every value is traceable to a filing and tag.
2. **SEC `companyfacts` API only.** Simplest, but it returns company-wide totals with no segment dimensions, so it can't isolate Gaming or G&NS. Used only to cross-check company totals.
3. **Scrape the HTML tables in filings or investor-relations pages.** Covers more (including Sony quarterly), but layout changes break it. Deferred.

Elijah delegated the choice ("wtv you think is best"). Annual and SEC-only is my call.

## Decided
- The comparison is Xbox (Microsoft) vs PlayStation (Sony), annual, from SEC filings.
- The outputs are an Excel variance report plus a README with charts.

## Left to the builder (my calls, marked)
- **Year range** *(my call):* every year where both companies disclose the gaming segment in XBRL. Expect about FY2018 onward. Confirm in a spike before writing the plan's tag map.
- **XBRL element and member names** *(my call):* found in a spike against real filings, then frozen in a `tag_map.yaml` with the source filing noted.
- **Restatements** *(my call):* the latest filing's value wins, and the superseded value is logged.
- **Microsoft's Activision acquisition (Oct 2023)** *(my call):* flagged in the commentary and on the charts.
- **Repo name** *(my call):* `console-war-financials`.

## Spike findings (2026-11-25, against real filings)
**Microsoft (CIK 789019).** The gaming fact is `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` with `srt:ProductOrServiceAxis`:
- The member is `msft:GamingMember` in the FY2019–FY2023 filings and is renamed `msft:XBOXMember` from the FY2024 10-K onward.
- Values seen, in USD bn:

  | FY | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---|---|---|---|---|---|---|---|
  | Revenue | 11.386 | 11.575 | 15.370 | 16.230 | 15.466 | 21.503 | 23.455 | 21.790 |

- There is **no gaming operating income and no hardware/content split in XBRL.** Microsoft gives the content & services split only as growth percentages in MD&A text, which is out of scope. So Xbox gets revenue only. The README must say so.
- 10-Ks older than FY2021 are not in the `submissions` "recent" list. They come from the paged `files` list.

**Sony (CIK 313838)** reports the segment as `GameAndNetworkServicesMember` on a segments axis. Three things change over time:
- **Accounting basis and concepts:**
  - US GAAP through the FY2020 20-F, using `us-gaap:Revenues` and `us-gaap:OperatingIncomeLoss`.
  - IFRS from FY2021, using `ifrs-full:Revenue` and `ifrs-full:ProfitLossFromOperatingActivities`.
  - FY2020 exists under both. Operating income is ¥342.192bn under GAAP and ¥341.718bn under IFRS. Rule: the latest filing wins, and the basis change is logged.
- **Prefixes:**
  - The member prefix is `sne:` through the 2018 20-F and `sony:` later.
  - The axes are `us-gaap:StatementBusinessSegmentsAxis` (GAAP) and `ifrs-full:SegmentsAxis` (IFRS).
- **Revenue measures and the product split:**
  - Revenue appears total (incl. intersegment), external-only, and intersegment. Use the total (`OperatingSegmentsMember`, no sales-channel member) as the headline.
  - The product split uses external customers.
  - The member set changed: `NetworkMember` / `HardwareAndOtherProductsAndServicesMember` early on, later `DigitalSoftwareAndAddOnContentMember`, `NetworkServicesMember`, `HardwareAndOthersMember` (plus others to enumerate). The plan maps them to 3–4 stable buckets via `tag_map.yaml`.

**Overlap range:** FY2019–FY2026 for both (8 years), covering the PS5/Series X launch and the Activision deal. Sony alone has FY2015+.

## Resolved
- SEC contact: set by Elijah in the gitignored `.env` as `SEC_USER_AGENT`. Code reads it from env and never prints it.
