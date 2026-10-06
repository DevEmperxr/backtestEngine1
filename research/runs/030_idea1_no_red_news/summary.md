# 030 — Idea 1 (023A) with no trading on red-news days (2023 + 2024)

**Date:** 2026-10-06
**File:** research/strategies/030_idea1_no_red_news.py (make)
**Status:** done: no effect; Idea 1 stays shelved

## In plain words
Same filter as 029 (no new trades on any day with a red ForexFactory USD or EUR event), applied to
Idea 1 (catch the top: 1m sweep at a 2·ATR 5m stretch, stop 1.5 × 5m ATR, target the 5m SMA20).
Compared with unfiltered 023A on the same years. User request.

## Hypothesis
*(registered before any filtered trade was simulated; practice years only)*
On red-news days, stretches are often real moves that keep going, so fading them at a sweep
fails more often. Skipping those days should help Idea 1. (029 found the opposite for Idea 2,
where red days carried the profit; this is a separate test.)

## Rules (fixed now)
023A unchanged; extra: no entry if the signal bar's New York date is a red-news date for USD or EUR
(research/regime/news.py). Main case = 1h trending, stretch with the trend; other contexts reported.

## Evaluation (fixed now)
With-trend: trades, net, expectancy, 95% CI, per year; filtered vs unfiltered; P&L of the removed
trades; equity + monthly chart. EURUSD 2023 + 2024 only. Audits as 023A, plus 0 trades on red days.

## Results
EURUSD 2023 + 2024; audits passed both years; 0 filtered trades on red days. Charts:
[filtered](idea1_no_red_news.png), [unfiltered](idea1_no_filter.png). (2024 results sit at the run
folder root: run_experiment's naming for EURUSD 2024 without a variant.)

| version | context | trades | net | exp/trade | 95% CI | 2023 | 2024 |
|---|---|---|---|---|---|---|---|
| no filter (023A) | trend_with | 273 | +37.8 | +0.14 | [−0.99, +1.26] | +56.7 | −18.9 |
| **no red-news days** | **trend_with** | 112 | **+13.1** | +0.12 | [−1.50, +1.83] | +26.1 | −13.1 |
| removed (red days) | trend_with | 161 | +24.7 | +0.15 | | | |
| no filter | sideways | 993 | −491.4 | −0.49 | [−1.05, +0.06] | −509.8 | +18.4 |
| no red-news days | sideways | 282 | −73.3 | −0.26 | [−1.10, +0.59] | −25.2 | −48.1 |

## Interpretation
**No effect.** Per-trade results are the same on red and non-red days (+0.12 vs +0.15
pips/trade with the trend), and the filter just removes 60% of the trades. The filtered
version is still ~zero and still negative in 2024. Red-news days are neither where Idea 1
fails nor where it succeeds. Idea 1 has no edge with or without the filter.

## Decision
**Do not adopt; Idea 1 stays shelved.** The news filter changes nothing for Idea 1 (029 showed it
hurts Idea 2).
