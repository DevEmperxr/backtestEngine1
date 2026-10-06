# 035 — Replication on 2024: Idea 1 fades in the first 2 h after the London open, 1h sideways

**Date:** 2026-10-06
**Files:** research/strategies/034_idea1_lon_ny.py (unchanged); results in research/runs/034_idea1_lon_ny/ (2024 run)
**Status:** exploring

## Hypothesis (from 034, registered before the 2024 run)
In 2023, Idea 1 (023A rules, window 08:00 London → 16:00 NY) fades **entered 03:00–04:59 New York
(the first two hours after the London open) with the 1h sideways** made **+320.5 pips on 207
trades**. Found post hoc among 39 hour × context slices. When the 1h is going nowhere, the
London-open push overshoots, sweeps a level, and comes back.

## Test (fixed now)
- Run the 034 strategy **unchanged** on **EURUSD 2024** (2024 has never been run with this wider window).
- Take exactly the same slice: entry hour (New York) ∈ {03, 04} and 1h context = sideways. Same
  sequencing and management as in 2023 (one position at a time over the whole window; flat
  16:00 NY).
- **Single pre-specified test on unseen data:** "replicates" if the slice's net pips > 0 **and**
  its per-trade 95% bootstrap CI excludes 0. "Direction holds" if net > 0 but the CI includes 0.
  "Fails" if net ≤ 0.
- Report the 2023 + 2024 combined figures and charts too (equity + monthly for the slice).

## Results
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
