# 030 — Idea 1 (023A) with no trading on red-news days (2023 + 2024)

**Date:** 2026-10-06
**File:** research/strategies/030_idea1_no_red_news.py (make)
**Status:** exploring

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
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
