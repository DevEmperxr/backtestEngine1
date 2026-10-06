# 051 — Final check: London fade (046) and the runner exits (050 B, C) on 2021 + 2022

**Date:** 2026-10-06 · **Status:** pre-registered. User asked: "test the origin idea, A, B and C on the
previous years to see if it breaks".

## Data
EURUSD **2021 and 2022**, test years (research/DATA_SPLIT.md). Never seen by the London fade or any
Idea 1 run on EURUSD (previously used only by the fix-fade runs 016–019). The news calendar covers
both years (Iran-DST clock handled up to 2022). 2025 and 2026 not touched. B and C also run on
practice year 2024 (A's 2024 is known: 210 trades, +191.6).

## Versions (files unchanged, as committed)
- **A** = research/strategies/046_london_fade_standalone.py (the original London fade)
- **B** = research/strategies/050_london_fade_runner.py make_b (break-even at the middle band, run to the
  opposite stretch band, out by 08:00 NY)
- **C** = 050 make_c (half off at the middle band + B on the rest)
Same costs/fills/news blackout as before. No parameter is changed after seeing these years.

## Pass bar (fixed now)
For A, on the two test years pooled:
- **PASS:** net pips > 0 after costs, AND target hit first more often than the spread-adjusted
  random-walk chance rate in BOTH years.
- **STRONG PASS:** PASS and the pooled 95% bootstrap CI of per-trade pips is above 0.
- **FAIL:** pooled net pips <= 0, or target-first at/below chance in either year.
Each year is reported separately as well. B and C: adopted over A only if they beat A on the pooled test
years AND on 2023+2024 combined; otherwise A stays.

## Results
_(filled after the run)_
