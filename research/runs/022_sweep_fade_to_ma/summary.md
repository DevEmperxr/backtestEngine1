# 022 — Idea 1: in a 1h trend, fade a stretched 5m move at a 1m liquidity sweep, target the 5m MA20 (2023)

**Date:** 2026-10-06
**File:** research/strategies/022_sweep_fade_to_ma.py (make = sweep entry; make_control = no-sweep entry)
**Status:** discarded

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
2023. Sweep: [main_2023](main_2023/), control: [control_2023](control_2023/). All audits passed (1,041 / 1,508
trades re-derived: 0 not a sweep of a confirmed swing, 0 not at the 2·ATR stretch).

| | context | trades | net pips | exp/trade | 95% CI | win | gross | TP-first vs null |
|---|---|---|---|---|---|---|---|---|
| **sweep** | **trend_with (primary)** | 236 | **−71.6** | −0.30 | [−1.05, +0.51] | 20.3% | **−1.5** | 16.4% vs 18.0% (z −0.6) |
| sweep | trend_against | 96 | +29.6 | +0.31 | [−0.91, +1.62] | 30.2% | +58.6 | 26.7% vs 23.8% (z +0.6) |
| sweep | sideways | 709 | −306.8 | −0.43 | [−0.88, +0.02] | 22.1% | −88.6 | 18.9% vs 19.8% |
| sweep | all | 1,041 | −348.8 | −0.34 | [−0.71, +0.04] | 22.5% | −31.5 | 19.1% vs 19.7% |
| control | trend_with | 258 | −63.9 | −0.25 | [−0.78, +0.34] | 15.9% | +12.9 | 13.3% vs 13.8% |
| control | trend_against | 189 | +29.7 | +0.16 | [−0.65, +1.08] | 18.5% | +84.1 | 17.3% vs 16.1% |
| control | sideways | 1,061 | −265.0 | −0.25 | [−0.54, +0.06] | 17.5% | +70.4 | 15.4% vs 14.9% |

- Primary H1/H2: −28.6 / −43.0. Exits (primary): 36 TP, 184 SL, 16 time.
- Stops are tiny (median ~2.8 pips sweep, ~1.6 control); spread ≈ 0.3 pips/trade ≈ 10% of risk.
- Sweep vs control in the primary context: −0.30 vs −0.25 pips/trade, i.e. no difference.

## Interpretation
**No edge.** In the main case (1h trending, 5m stretched with the trend, 1m sweep) price
reached the 5m MA20 before the stop **no more often than chance** (16.4% vs 18.0% for a
random entry with the same stop/target). Before costs it was flat (−1.5 pips over 236
trades); the spread made it negative. **The sweep adds nothing** over simply fading the first
touch of the 2·ATR band (control). The 1h context doesn't help either: "with trend" is not
better than sideways, and "against trend" is slightly positive in both versions but small
and inside noise.

Mechanically (charts): the sweep stop is usually 1.5–5 pips, which is inside normal 1m noise,
so most trades are stopped within minutes, before any reversion could play out. This matches
brick 1b: a stretched move tends to keep going, and a single 1m poke-and-close is not enough
to say it has turned.

## Decision
**discard (as specified).**
**Why:** primary subset −71.6 pips, gross ≈ 0, 95% CI [−1.05, +0.51], negative in both halves,
TP-first rate at the random null; the sweep does not beat the no-sweep control. Possible
follow-ups (each a new pre-registered trial): a stop sized to 5m noise instead of the sweep
bar; a 5m sweep instead of 1m. The user's Idea 2 (wait for the 5m turn) is the separate next idea.
