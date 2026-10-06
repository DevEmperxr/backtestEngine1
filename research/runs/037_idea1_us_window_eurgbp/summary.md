# 037 — Test on EURGBP: Idea 1, 1h trending, entries 08:00–10:00 New York only

**Date:** 2026-10-06
**Data:** existing run-027 trade logs (023A rules on EURGBP), 2023 and 2024 only (user's rule)
**Status:** exploring

## Hypothesis (from 033, registered before looking at EURGBP by hour)
On EURUSD 2023 + 2024, Idea 1 (023A) trades with the 1h trending, entered **08:00–09:59 New York**,
made +161.6 pips on 131 trades, positive in both years (found by slicing by hour).

## Test (fixed now)
- Take the 027 EURGBP trade logs for **2023 and 2024** (023A rules, unchanged; never examined by
  hour). Select: context = trending with the trend AND entry hour (New York) ∈ {08, 09}.
- "Replicates" if pooled net > 0 AND the per-trade 95% CI excludes 0. "Direction holds" if net > 0 in
  both years. "Fails" otherwise.
- Caveat stated now: Idea 1 lost heavily on EURGBP overall (027: spread ≈ 15–20% of risk), so this is
  a hard test.

## Results
_(filled after the run)_

## Decision
_(filled after the run)_
