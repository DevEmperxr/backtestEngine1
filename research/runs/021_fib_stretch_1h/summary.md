# 021 — How far does price stretch from the 1h MA20 before pulling back? Fibonacci-σ bands (2023)

**Date:** 2026-10-06
**Files:** research/regime/fib_stretch.py
**Status:** exploring
**Brick 1b** of the "fade the stretch back to the MA" programme. Measurement only, no trades.

## Question
*(registered before any stretch was computed on 2023)*

1. In 2023, how far (in units of 1h volatility) does EURUSD typically get from its 1h
   MA20 before coming back to it? This is a ruler for "how far is too far".
2. Do **Fibonacci multiples** of σ mark turning points more than other multiples do? (No
   research evidence says they should; this is a direct check.)

## Definitions (fixed now)
- **1h MA20 and σ20:** SMA and SD of the last 20 **closed** 1h mid closes, taken as-of each
  1m bar (as-of backward on close_time: an hour still forming is never used).
- **Stretch z_t** = (1m mid close − MA) / σ, on 1m bars (mid from 1s via `resample`).
- **Excursion:** a maximal run of 1m bars with z on one side of 0. It ends when the 1m
  close crosses back through the MA (z changes sign). **Peak** = the excursion's largest
  |z| using the 1m mid high (up-excursions) / low (down-excursions) against the MA/σ in force.
- **Bands:** ±0.382, 0.618, 1.0, 1.618, 2.618, 4.236 σ (user: "Bollinger, but Fibonacci
  instead of SDs").
- Sample: all 2023 excursions starting Mon–Fri; also reported for the subset whose peak
  falls in the user's window (07:00 New York → 16:00 London).

## Outputs (fixed now)
1. **Peak distribution:** share of excursions whose peak reaches each band; median, p75,
   p90, p95 of peak |z|; duration of excursions.
2. **Turning probability (hazard)** on a 0.1σ grid from 0.1 to 5.0: P(peak < L + 0.1 |
   peak ≥ L), with bootstrap CIs over excursions.
3. **Fibonacci test:** for each level, local excess = hazard in the 0.1σ bin starting at
   the level − mean hazard of the bins 0.2σ below and 0.2σ above. Fibonacci levels
   {0.382, 0.618, 1.618, 2.618} vs control levels {0.5, 0.8, 1.3, 2.0, 2.2}. **Fibonacci
   "matters" only if** the mean local excess of Fibonacci levels exceeds that of the control
   levels with a 95% bootstrap CI (resampling excursions) that excludes 0. Otherwise the
   bands are kept as a ruler and the Fibonacci spacing is noted as unsupported.

## Notes
- 2023 is the development year; any use of these numbers in a strategy needs confirmation
  on other years.
- An "excursion" ends at the MA. That is not the same as the 5m MA20 target of trade B
  (that relation is brick 2).

## Results
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
