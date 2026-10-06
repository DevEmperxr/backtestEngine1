# 021 — How far does price stretch from the 1h MA20 before pulling back? Fibonacci-σ bands (2023)

**Date:** 2026-10-06
**Files:** research/regime/fib_stretch.py
**Status:** done: Fibonacci not supported; no exhaustion level
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
2023. [results_2023.json](results_2023.json), [excursions_2023.parquet](excursions_2023.parquet).
σ = population SD of the last 20 closed 1h closes (Bollinger convention; the registration
said "SD" without specifying).

**Peaks** (|z| at the excursion's extreme):

| sample | excursions | median peak | p75 | p90 | p95 | median duration | p90 duration |
|---|---|---|---|---|---|---|---|
| all (weekday starts) | 5,060 | 0.22σ | 0.64σ | 1.80σ | 3.22σ | 4 min | 106 min |
| peak in user window | 1,254 | 0.46σ | 1.33σ | 3.51σ | 4.94σ | 5 min | 234 min |

**Share of excursions reaching each band, and continuation odds:**

| band | all: reached | window: reached | window: P(reach next band \| reached this) |
|---|---|---|---|
| 0.382σ | 35.5% | 55.0% | 0.382→0.618: 78% |
| 0.618σ | 25.5% | 42.9% | 0.618→1.0: 72% |
| 1.0σ | 17.3% | 31.0% | 1.0→1.618: 69% |
| 1.618σ | 11.2% | 21.5% | 1.618→2.618: 65% |
| 2.618σ | 6.5% | 14.0% | 2.618→4.236: 54% |
| 4.236σ | 2.8% | 7.6% | |

**Turning probability** (P the excursion peaks within the next 0.1σ, given it reached L),
window sample: 0.5σ 8.6%, 1.0σ 8.7%, 1.5σ 5.5%, 2.0σ 2.7%, 2.5σ 2.2%, 3.0σ 2.6%, 4.0σ 2.9%
(all sample: 11.4% → 8.7% → 6.3% → 5.0% → 4.0% → 5.0% → 4.3%). **It falls as the
stretch grows.**

**Fibonacci test:** fib − control mean local excess = −0.004 (95% [−0.018, +0.009]) all;
+0.006 ([−0.012, +0.025]) in-window. **Fibonacci levels are not special** in either sample.

## Interpretation
1. **There is no "too far" level where a pullback becomes likely.** The chance of turning
   *drops* the further price gets from the 1h MA20: about 9% per 0.1σ near 1σ, about 2–3% beyond
   2σ (in-window). Once a move has stretched, it tends to keep stretching (fat tails /
   momentum at this scale), the opposite of what a mechanical "fade at 2.618σ" assumes.
2. **Fibonacci spacing adds nothing.** Turning probability changes smoothly with distance.
   Fib levels are no more likely to stop price than nearby non-fib levels. The bands work
   as a ruler, but the ruler could just as well be 0.5/1/1.5/2.
3. Most excursions are tiny (median 4–5 minutes, 0.2–0.5σ): 1m price whips across the MA
   often. The meaningful ones are the ~20–30% that reach 1σ+.
4. Caveat: σ of 20 hourly closes collapses in quiet periods, giving very large z (p99 ≈ 8σ).
   An ATR-based unit would be more stable; worth checking before using z in a strategy.

Together with brick 1 (a clean 1h trend tends to be followed by chop, as a hint) the
picture is mixed: big stretches keep extending, but a clean 20-hour trend tends to stall
afterwards. For trade B that means **fading purely on distance from the 1h MA is not
supported**. A turn needs a trigger (the 1m liquidity sweep of brick 3), not just a level.

## Decision
**Keep the σ-band ruler as a descriptive tool; drop the Fibonacci spacing** (no evidence).
**Do not use "price beyond band X" as a fade signal by itself:** turning odds fall with
distance. Next: brick 2 should measure snap-back to the 5m MA20 conditioned on stretch and on
the 1h's recent trend, and brick 3 whether a 1m sweep marks the turn. Confirm on other
years before use.
