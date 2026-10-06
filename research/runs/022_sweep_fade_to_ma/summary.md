# 022 — Idea 1: in a 1h trend, fade a stretched 5m move at a 1m liquidity sweep, target the 5m MA20 (2023)

**Date:** 2026-10-06
**File:** research/strategies/022_sweep_fade_to_ma.py (make = sweep entry; make_control = no-sweep entry)
**Status:** exploring

## In plain words
The 1h is trending up. Price on the 5m runs too far above its 20 MA. On the 1m, price pokes
above a recent high and closes back below it (a "liquidity sweep": late buyers trapped, the push
out of fuel). We sell, aiming for the 5m 20 MA, with a stop just above the sweep. Mirrored for
1h downtrends. The user's Idea 1 (catch the top); Idea 2 (wait for the turn) is separate.

## Hypothesis
*(registered before any trade was simulated on 2023)*

When price overshoots in the direction of the 1h trend, it tends to come back to its 5m
average before carrying on. A 1m sweep of the most recent swing marks the moment the overshoot
fails. Brick 1b warned that distance alone does not produce turns (turning odds fall as
stretch grows), so the sweep, not the distance, is the trigger. **The sweep should
make this better than fading at the stretch alone** (the control).

Prior: sceptical. Osler (2003): stop orders cluster beyond swing levels, but triggering them
usually accelerates moves. Run 008 (fading round-number rejections without context) was
random. Here the sweep only counts in context.

## Rules (fixed now)
All prices are mid (bid+ask)/2. Bars from 1s via `resample`. Higher timeframes use **closed
bars only** (as-of backward on close_time).
- **1h context** (last closed 1h bar): ER20 of 1h closes and the slope of the 1h SMA20
  (SMA20_t − SMA20_{t−5}). **Trending up** if ER20 ≥ 0.32 and slope > 0; **trending down** if
  ER20 ≥ 0.32 and slope < 0; otherwise **sideways**. (0.32 = top third of 2023 1h ER20 values,
  fixed for all future years.)
- **5m stretch** (last closed 5m bar's SMA20 and ATR14): the signal 1m bar's high ≥ SMA20 + 2·ATR14
  (stretched up), or its low ≤ SMA20 − 2·ATR14 (stretched down).
- **1m swing high/low:** a bar whose high (low) is the highest (lowest) of the 7 bars centred on it
  (3 each side). It only becomes usable **3 bars later** (confirmation; no hindsight). The
  level used is the most recent swing confirmed before the signal bar.
- **Sweep (short):** signal 1m bar's high > the latest confirmed 1m swing high AND its close <
  that level, while stretched up. **Sweep (long):** low < latest confirmed swing low AND close >
  it, while stretched down.
- **Entry:** next 1m open. **Stop:** 1 pip beyond the sweep bar's high (low), measured from the
  signal close. **Target:** the 5m SMA20 (last closed 5m bar); skip if price is already beyond it.
- **Trade direction vs context:** every sweep is simulated in every context, then results are
  split. **Primary = "trending, stretch with the trend"** (stretch up + short in a 1h uptrend;
  stretch down + long in a downtrend). The other contexts are reported for comparison.
- Window: entries 07:00 New York → 16:00 London, Mon–Fri; everything flat at 16:00 London;
  one position at a time; `exit_on_opposite_signal = False`.
- **Control (`make_control`):** same context, stretch, target and timing, but enter at the first
  1m bar that reaches the 2·ATR stretch (no sweep needed); stop 1 pip beyond that bar's extreme.
  This answers "does the sweep add anything?".

## Evaluation (fixed now)
- Full adversarial suite on the primary subset and on all trades; H1/H2; spread-adjusted
  random-walk null (TP-first rate vs (SL − spread)/(SL + TP)).
- **Primary verdict (dev year 2023):** primary subset expectancy 95% CI excludes 0 AND both
  halves positive AND TP-first rate ≥ 2 SE above the null. Pass = "candidate, confirm on other
  years"; nothing is trusted on 2023 alone.
- **Sweep vs control:** primary-subset expectancy difference, reported with both CIs.
- Context table: trades, net, expectancy, win rate, TP-first vs null for trending-with,
  trending-against and sideways.
- Lookahead audit: entry at the signal bar close; independent re-derivation (1m pivots
  recomputed in plain Python with their confirmation delay; 5m SMA/ATR from 1s-rebuilt 5m bars)
  that every signal bar is a sweep of a confirmed swing while stretched.

## Results
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
