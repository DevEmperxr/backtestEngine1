# 020 — Trend-detector scorecard: which detectors predict the next 20 bars' trendiness? (5m / 15m / 1h, 2023)

**Date:** 2026-10-06
**Files:** lib/signals.py (detector primitives), research/regime/trend_scorecard.py
**Status:** done: no persistent-trend detector found
**Brick 1 of the "fade the stretch back to the MA20 in a trending market" programme** (the user's trade B).

## Question
*(registered before any detector was computed on 2023)*

At a 5m bar close, can a detector built from past bars only tell us whether the **next 20
bars (100 min, the span of the 5m MA20)** will be trending or choppy, better than the time
of day alone and better than a volatility-preserving random walk?

## Yardstick (future, the label only, never an input)
**Future Efficiency Ratio:** FER_t = |c_{t+20} − c_t| / Σ_{k=t+1..t+20} |c_k − c_{k−1}|, on 5m mid
closes. 1 = straight line, ≈0 = chop.

## Candidate detectors (fixed now; past bars only, value known at bar t's close)
1. **ER20:** Kaufman efficiency ratio over the last 20 bars.
2. **ADX14:** Wilder ADX(14), Wilder smoothing.
3. **SLOPE:** |SMA20_t − SMA20_{t−5}| / ATR14_t.
4. **R2_20:** R² of a straight-line fit of the last 20 closes on time.
5. **CHOP14 (inverted):** −Choppiness Index(14) = −100·log10(ΣTR₁₄ / (maxH₁₄ − minL₁₄)) / log10(14).
6. **VR4_100:** variance ratio Var(4-bar returns) / (4·Var(1-bar returns)) over the last 100 bars.
7. **AC1_50:** lag-1 autocorrelation of 5m returns over the last 50 bars.

## Sample
2023 EURUSD 5m bars (resampled from 1s, mid prices). Readings at bars whose close_time is in
[07:00 America/New_York, 16:00 Europe/London), Mon–Fri, whose 20 future bars are all present
(no gap). All indicator warmups computed on continuous data.

## Scoring (fixed now)
- **Primary metric:** Spearman rank correlation ρ(detector_t, FER_t). 95% CI by **block
  bootstrap over days** (resample whole trading days, 2,000 resamples, seed 0), because
  readings within a day overlap and are correlated.
- **Secondary:** mean FER in the detector's top quintile minus bottom quintile.
- **Baseline 1, time of day:** predictor = mean FER for that 5-minute slot, **cross-fitted**
  (slot means from H1 used to score H2 and vice versa, so the baseline never sees its own
  data). A detector must add to this: also report the partial ρ after removing the
  time-of-day effect (ρ between detector and FER residuals from the slot means).
- **Baseline 2, sign-randomised null:** keep every 5m return's size and flip its sign at
  random (whole pipeline recomputed: prices → detectors → FER), 20 surrogates (seeds 1–20).
  This keeps volatility clustering and time-of-day volatility but removes any real direction
  persistence. Report each detector's null ρ range.
- **Stability:** ρ separately on H1 (Jan–Jun) and H2 (Jul–Dec) 2023.

## What counts as a useful detector (fixed now)
All of: (a) 95% CI of ρ excludes 0; (b) real ρ above the maximum of its 20 null ρ's; (c)
partial ρ after the time-of-day adjustment > 0 with a CI excluding 0; (d) same sign and
ρ > 0 in both H1 and H2. Ranking among useful detectors by partial ρ. With 7 detectors,
a detector that only clears (a) is reported as "weak".

## Notes
- This is a measurement brick, not a strategy: no trades, no P&L.
- 2023 is the user's choice of development year. A winner here gets confirmed on other years
  (2021, 2022, 2025) before being used as a filter. 2026 stays untouched.

## Amendment (2026-10-06, before any detector was computed)
After the user pointed out that a higher-timeframe pullback is a lower-timeframe trend
switch, the scorecard is run on **three timeframes** instead of one, with identical
definitions in bars: **5m, 15m and 1h** (20 bars back, 20 bars ahead: ~1h40m, ~5h, ~20h).
- Readings: 5m and 15m bars closing in the user's window; 1h bars closing in the window
  (fewer readings per day). Future 20 bars must be contiguous in time (no weekend hole).
- Bars: built from 1m mid OHLC (1m from 1s via `resample`), aggregated per timeframe.
- Sign-randomised null: built at the 1m level (each 1m bar's close-to-close return gets a
  random sign; a flipped bar's OHLC shape is mirrored), then aggregated like the real data.
- Bootstrap: day-level resampling via per-day sufficient statistics on globally ranked data
  (Pearson-of-ranks approximation to Spearman), 2,000 resamples.
- **7 detectors × 3 timeframes = 21 tests.** Criteria (a) and (c) use **99.8% CIs**
  (Bonferroni 0.05/21) instead of 95%. (b) and (d) unchanged.
- Time-of-day slot for 1h = the hour.

## Results
2023, readings in the user's window. [results_2023.json](results_2023.json). ρ = Spearman(detector_t, FER_t).

| detector | 5m ρ (n=12,612) | 15m ρ (n=4,204) | 1h ρ (n=840) |
|---|---|---|---|
| ER20 | +0.016 | −0.001 | **−0.113** (95% [−0.21, −0.01]) |
| ADX14 | +0.010 | −0.034 | −0.056 |
| SLOPE | +0.004 | −0.011 | −0.071 |
| R2_20 | +0.022 | −0.018 | **−0.150** (95% [−0.25, −0.05]; null range [−0.134, +0.083]) |
| CHOP14_inv | +0.023 | +0.010 | −0.026 |
| VR4_100 | +0.016 | −0.009 | +0.004 |
| AC1_50 | +0.038 | +0.012 | +0.063 |
| time-of-day baseline | +0.021 | −0.030 | +0.003 |

- **No detector is "useful" or even "weak" (in the positive direction) on any timeframe.**
  Every 99.8% CI includes 0, and every 5m/15m ρ sits inside its sign-randomised null range.
- 1h exception, in the **opposite** direction: a clean 20-hour trend (high R²/ER) was followed
  by a *less* efficient next 20 hours: R2_20 ρ −0.150 (negative in H1 −0.149 and H2 −0.144,
  below the minimum of its 20 null ρ's), ER20 −0.113. The 95% CIs exclude 0; the registered
  99.8% CIs do not ([−0.296, +0.021] and [−0.257, +0.020]).
- Mean future ER ≈ 0.24–0.26 at all timeframes; the time of day adds nothing either.

## Interpretation
**In 2023 EURUSD, "is it trending now?" does not predict "will it trend over the next 20
bars?" on 5m, 15m or 1h.** All seven detectors describe the past well (that's what they are
built for), but trendiness has no measurable persistence at these horizons. That holds
whether trend is measured by slope, ADX, efficiency, linearity, choppiness, variance ratio
or autocorrelation. A trend filter built on "it has been trending, so it will keep trending"
has nothing to stand on here.

The only signal points the other way, at 1h: after a clean 20-hour trend, the next ~20
hours tend to be choppier (exhaustion / consolidation). It is not significant at the
registered 21-test level, so it is a hypothesis to check on other years, not a finding.
It is, however, the direction the user's trade B would want: trends that have run
cleanly tend to stall.

## Decision
**No detector adopted as a "trend persists" filter.** Carry forward one hypothesis for
confirmation on other years: *1h R²/ER over the last 20 hours is negatively related to the
next 20 hours' efficiency* (trend exhaustion). Brick 2 (does the 5m stretch revert to the
MA20 more when the 1h has been trending?) can still be tested directly, but "1h trending"
there must be read as "the last 20 hours trended", not as a state expected to continue.
