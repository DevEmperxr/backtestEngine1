# 029 — Idea 2 (025 B and C) with no trading on red-news days (2023 + 2024)

**Date:** 2026-10-06
**File:** research/strategies/029_idea2_no_red_news.py (make_b, make_c); calendar in research/regime/news.py
**Status:** exploring

## In plain words
The user's filter: **no new trades on any day with a red (high-impact) ForexFactory event for
either currency of the pair.** For EURUSD that means any red USD or EUR event. Applied to Idea 2
(stretch → confirmed 5m turn → ride the move) with targets B (2× risk) and C (last 1h swing),
everything else unchanged. Compared with the unfiltered 025 trades.

## Hypothesis
*(registered before any filtered trade was simulated; practice years only, per the user's rule)*
On red-news days, a 5m stretch is often driven by real news and keeps going, so the turn
pattern fails more often. Removing those days should raise the per-trade result.

## Data (checked before registering)
- Calendar: ForexFactory "High Impact Expected" events from the Tropstan dataset (MIT,
  2007–2025-04). About half the 2023–2024 red rows have no time (stored as 00:00). Their file date
  is used; timed rows use the New York date. Check: all 12 NFP and all 12 CPI dates of 2023 found.
- EURUSD red weekdays: 178 (2023) and 168 (2024) of ~260, so roughly 2/3 of days are skipped. The
  user chose this full version knowing it leaves few trades (expected ~30–40 with-trend trades
  over two years).

## Rules (fixed now)
025 rules unchanged (1h context, 5m stretch 1.5·ATR, 5m swings k=2, lower-high → break, stop beyond
the lower high, window, flat 16:00 London). **Extra:** no entry if the signal bar's New York date
is a red-news date for USD or EUR.

## Evaluation (fixed now)
- Per year and both years: with-trend trades, net, expectancy, 95% CI; filtered vs unfiltered
  025 on the same years. Equity curve and monthly P&L (both years, with-trend).
- Expected to be far too few trades to conclude anything; reported as descriptive.
- Practice years only (2023, 2024). Audit: every trade's NY date is not a red date (plus the 025
  structure audit).

## Results
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
