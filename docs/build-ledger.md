# SDD ledger — plan: C:/Users/ual-laptop/Documents/Claude Work/console-war-financials/docs/plan.md
Spec: docs/design.md
Branch: build

## Pre-flight
- T1→T5: FRED fetch needs no UA but should be cached. Ruling: fx.load_dexjpus takes a `client_get` callable; pipeline passes `cwf.sec.cached_get(url, cache_dir)` (plain cached GET, no UA) — cost if wrong: none.
- T2→T4: Fact uses local names (no prefix); tag_map uses local names; basis from concept local name via `basis:` map — consistent.
- T3→T4/T8: Filing fields consumed by extract (accession, filing_date) — consistent.
- T4→T6: Row fields → raw_rows columns 1:1 — consistent.
- T6→T7: segment_year, restatements, v_yoy, v_sony_mix, v_sony_margin, v_head_to_head consumed by report/charts — consistent.
Task 1: Ruling: added test_gives_up_after_retries and an offline mode + cached_get (used by T5/T8 per pre-flight) — cost if wrong: none.
Task 1: complete (commits 952f302..943ad6e, tests: python -m pytest -q → 6 passed in 0.43s)
Task 2: complete (commits 943ad6e..806f4db, tests: python -m pytest -q → 11 passed in 0.41s)
Task 3: complete (commits 806f4db..3e1abe0, tests: python -m pytest -q → 15 passed in 0.40s)
Task 4: Ruling: tag_map uses a LIST of rules per metric (concepts, require{axis:[members]}, exactly_dims) instead of the plan's `axis|alias` keys, because Sony's axes and concepts change together (GAAP Revenues -> ASC 606 RevenueFromContract... -> IFRS Revenue) — cost if wrong: none.
Task 4: Ruling (live enumeration via cwf.explore): Microsoft revenue = RevenueFromContract... x ProductOrServiceAxis {GamingMember FY2016-FY2025, XBOXMember FY2024-FY2026}; older SalesRevenueNet XboxMember (FY2013-17, pre-ASC 606) excluded. Sony revenue/revenue_external/operating_income mapped across GAAP (to FY2021) and IFRS (FY2021+); see tag_map.yaml comments.
Task 4: Ruling: Sony product mix = the 3 buckets Sony reports (not the plan's 4): digital software, network services, hardware & others; FY2017+ only from RevenueFromContract/Revenue concepts. The pre-2019 `Revenues` x NetworkMember meant digital software + network combined, so mixing it in would be apples-to-oranges — cost if wrong: mix starts FY2017 not FY2014.
Task 4: live sanity on all real filings: 0 same-filing conflicts; Sony buckets / external = 1.0000 every year FY2017-FY2026; MSFT FY2016-FY2026, Sony FY2013-FY2026.
Task 4: complete (commits 3e1abe0..6bcf1de, tests: python -m pytest -q → 22 passed in 0.47s)
Task 5: complete (commits 6bcf1de..c355459, tests: python -m pytest -q → 25 passed in 0.53s)
Task 6: Ruling: segment_year picks one row per key with row_number (latest filing, then accession, then concept); check (d) separately fails if the winning filing reports two different values — so a same-filing conflict is caught, never silently resolved. Added check (e) every row has a USD value. tests/helpers.py holds shared test builders — cost if wrong: none.
Task 6: live on real data: CHECKS PASSED; 1 restatement (Sony FY2021 OI 342.192 -> 341.718, GAAP->IFRS); head-to-head FY2016-FY2026, Xbox share 35.3%-43.4%.
Task 6: complete (commits c355459..a13c6d5, tests: python -m pytest -q → 36 passed in 1.89s)
Task 7: Ruling: plan's EVENTS said FY2024 = "first full year including Activision" — wrong (deal closed Oct 13 2023, inside MS FY2024 Jul23-Jun24, ~8.5 months). FY2024 = partial, FY2025 = first full year; also PS5 / Series X|S launch (Nov 2020) on FY2021. test_activision_partial_year_is_not_called_full RED->GREEN — cost if wrong: none.
Task 7: Ruling: dataviz validator needs node (not installed); ran the same OKLab/Machado CVD dE + WCAG contrast math in Python: Xbox #107c10 vs PS #2a78d6 dE normal 28 / protan 26.5 / deutan 26.1 / tritan 9.2 (all >= 8), contrast 5.2 & 4.3; mix palette (blue/orange/aqua ref slots) adjacent dE >= 9.2; aqua 2.74:1 < 3 -> relief rule satisfied by direct labels on every line + Excel table. Static PNGs (README) so no hover layer; the Excel workbook is the table view — cost if wrong: minor.
Task 7: rendered real charts and eyeballed them; moved legends above plots (collided with FY2017 hardware point) and split footnotes to two lines.
Task 7: complete (commits a13c6d5..b02a80c, tests: python -m pytest -q → 43 passed in 4.66s)
Task 8: Ruling: run() takes cache/reports/charts dirs (testable); README findings verified by query against the model (one README claim, intersegment "about 2-3%", corrected to 2-5%). Workflow runs pytest before the pipeline. Live: 24 filings, 201 rows, 83 values, 1 restatement, checks passed; online vs --offline PNGs identical; hand cross-check MSFT FY2021 15.370bn, Sony FY2026 rev 4,685.651bn, Sony FY2024 OI 290.184bn all OK.
Task 8: complete (commits b02a80c..7be6b39, tests: python -m pytest -q → 44 passed in 6.04s)
Final review: self-review (no subagent tool use without Elijah's ask). Read review package 952f302..7be6b39 against plan Review Focus 1-5: all five have tests and pass.
Final: fixed (Important) stale cache — submissions lists and FRED CSV were cached forever, so a local `python -m cwf.pipeline` would never see a new 10-K/20-F or new FX days (Actions was unaffected: fresh runner). Now refresh=True for growing lists when online; filed archives stay cached; --offline still cache-only — test_refresh_refetches_when_online, test_refresh_uses_cache_when_offline, test_cached_get_refresh, test_submission_lists_are_refreshed_archives_are_not RED->GREEN, suite 48/48. Live run re-fetched lists, outputs unchanged.
Final: minor (deferred): report_xlsx treats a prior value of exactly 0 as "no prior" (never occurs in this data).
Final: minor (deferred): report assumes every Sony year has a revenue row (true for all real filings; checks would not catch a year with only buckets).
