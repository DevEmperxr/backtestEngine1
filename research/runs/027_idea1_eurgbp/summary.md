# 027 — Idea 1 (023A, unchanged) on a second market: EURGBP 2021–2024

**Date:** 2026-10-06
**File:** research/strategies/023_sweep_fade_rework.py (make_a); results in research/runs/023_sweep_fade_rework/a_EURGBP_<year>/
**Status:** exploring

## Why
User request. EURGBP has never been looked at in this project. Running Idea 1 with the **exact**
023A rules (including the 0.32 1h-ER trend threshold derived from EURUSD 2023, and the 2·ATR
stretch / 1.5·ATR stop, which scale with each pair's own volatility) is a clean replication on
unseen data. Registered before any EURGBP result was computed. 2025 is excluded (still
downloading).

## Question / criteria (fixed now)
Does Idea 1's with-trend case make money on EURGBP?
- Per year (2021, 2022, 2023, 2024): with-trend trades, net, expectancy, TP-first vs the
  spread-adjusted null; context table (with / against / sideways).
- **Pooled 2021–2024 with-trend:** "replicates" only if the expectancy 95% CI excludes 0 AND at
  least 3 of 4 years are positive. Also reported: whether sideways is worse than with-trend
  (the 2023-EURUSD pattern that 2024-EURUSD did not repeat).
- Audits as 023A (sweep/stretch re-derived on 1s-rebuilt bars; ATR stop checked).
- Caveat: EURGBP spreads relative to its moves may differ from EURUSD; gross vs net is reported.

## Results
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
