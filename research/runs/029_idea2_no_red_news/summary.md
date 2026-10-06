# 029 — Idea 2 (025 B and C) with no trading on red-news days (2023 + 2024)

**Date:** 2026-10-06
**File:** research/strategies/029_idea2_no_red_news.py (make_b, make_c); calendar in research/regime/news.py
**Status:** done: the filter hurts; not adopted

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
EURUSD, with-trend trades, 2023 + 2024. Audits passed (0 structure failures each year; 0 filtered
trades on red days). Charts: [B](idea2_B_no_red_news.png), [C](idea2_C_no_red_news.png).

| target | version | trades | net | exp/trade | 95% CI | 2023 | 2024 |
|---|---|---|---|---|---|---|---|
| B (2R) | no filter (025) | 99 | +72.9 | +0.74 | [−1.90, +3.43] | +23.1 | +49.8 |
| B (2R) | **no red-news days** | 36 | **+23.2** | +0.64 | [−3.57, +5.21] | +30.4 | **−7.2** |
| B | trades removed (on red days) | 63 | **+49.7** | | | | |
| C (1h swing) | no filter (025) | 109 | +88.3 | +0.81 | [−1.76, +3.57] | +25.8 | +62.5 |
| C (1h swing) | **no red-news days** | 43 | **+4.3** | +0.10 | [−3.36, +3.75] | +28.2 | **−23.8** |
| C | trades removed (on red days) | 66 | **+84.0** | | | | |

## Interpretation
**The filter hurts.** About 2/3 of Idea 2's with-trend trades fall on red-news days, and those
trades carried most of the profit (B +49.7 of +72.9; C +84.0 of +88.3). The remaining
quiet-day trades are roughly flat and negative in 2024 for both targets. The hypothesis
(news-day stretches keep going, so the turn fails) is the opposite of what happened. If
anything, Idea 2 works *better* on news days, perhaps because news days produce the big
stretches and decisive turns the setup needs. Sample sizes are tiny (36–66 per group),
so neither "works on news days" nor "fails on quiet days" is established.

## Decision
**Do not add the red-news filter to Idea 2.** It removed the profitable trades. Possible
follow-up (new trial, practice years only): the opposite, "news days only", or a narrower
"no trades in the 30 min around a red event". Keep Idea 2 unfiltered (025 B/C) as the version.
