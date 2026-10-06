# 044 — Run 042 (two windows) with no trading on red-news days, EURUSD 2023 + 2024

**Date:** 2026-10-06 · file: research/strategies/044_two_windows_no_red_news.py
**Status:** done. Filter NOT adopted overall

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
Lookahead audit clean both years. Comparison: research/regime/compare_044.py -> comparison.json.

| | London 042 | London 044 | NY 042 | NY 044 | Both 042 | Both 044 |
|---|---|---|---|---|---|---|
| trades | 434 | 150 | 157 | 66 | 591 | 216 |
| pips 2023 / 2024 | +322 / +140 | +3 / +24 | −25 / +158 | +30 / +48 | +298 / +298 | +32 / +72 |
| per trade (95% CI) | +1.07 [+0.25, +1.91] | +0.18 [−1.13, +1.52] | +0.85 [−0.94, +2.72] | +1.17 [−1.25, +3.69] | +1.01 [+0.21, +1.79] | +0.48 [−0.69, +1.70] |
| fair Sharpe | 1.75 | 0.20 | 0.64 | 0.79 | 1.77 | 0.65 |
| max DD (pips) | −147 | −95 | −122 | −60 | −126 | −79 |
| months positive | 16/24 | 11/24 | 16/24 | 14/24 | 19/24 | 11/24 |

- **London fade: the filter wipes it out** (+462 -> +27). Its profit comes from red-news days.
- **NY open: slightly better per trade and positive in both years** (+29.5 / +47.9), but only 66 trades
  and the CI is very wide. The total falls (+133 -> +77). Weak hint, not evidence; this split was already
  visible in 043, so it isn't an independent finding.
- Combined: much worse (+595 -> +104). Same lesson as 029: news days are where these trades make money.

