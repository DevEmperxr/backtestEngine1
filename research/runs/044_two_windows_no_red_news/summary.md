# 044 — Run 042 (two windows) with no trading on red-news days, EURUSD 2023 + 2024

**Date:** 2026-10-06 · file: research/strategies/044_two_windows_no_red_news.py
**Status:** pre-registered (user request)

## What
Exactly run 042 (Idea 1 rules; entries only 03:00–04:59 NY with the 1h sideways, or 08:00–09:59 NY
with the 1h trending), plus: **no new entries on any New York calendar day that has a ForexFactory
High Impact (red) event for USD or EUR**. Same rule as runs 029/030. Open trades are unaffected.

## What we compare
042 vs 044, per window and combined: net pips per year, per trade with 95% CI, fair Sharpe,
drawdown, months positive. Earlier evidence: the filter hurt Idea 2 (029) and did nothing for
Idea 1 overall (030). In the 043 split, NY-window trades on non-news days were +29.5 / +47.9 and on
news days −53.9 / +109.6, so no clear expectation. Red days are about 60% of weekdays, so expect
far fewer trades.

## Results
_(filled after the run)_
