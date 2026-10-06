# 023 — Idea 1 reworked: (A) 1m sweep with a 5m-noise-sized stop, (B) sweep on the 5m (2023)

**Date:** 2026-10-06
**File:** research/strategies/023_sweep_fade_rework.py (make_a, make_b)
**Status:** exploring

## In plain words
022 failed because the stop just above a 1m sweep (≈2.8 pips) sits inside normal 1m noise:
most trades were stopped within minutes. Two fixes, tested as separate trials:
- **A:** same 1m sweep entry, but stop = **1.5 × the 5m ATR** from the entry (about one normal
  5m candle).
- **B:** the sweep is on **5m candles**: a stretched 5m candle pokes above (below) the latest
  confirmed 5m swing high (low) and closes back inside; enter at the next 5m open; stop 1 pip
  beyond that 5m candle.

## Hypothesis
*(registered before any 023 trade was simulated; data-informed by 022's result, so these
are trials 2 and 3 of Idea 1 on 2023)*

If the 022 idea was right but its stop was too tight, giving the trade room for normal 5m
noise (A), or reading the sweep on the 5m where its stop is naturally wider (B), should
turn the primary context positive and lift the TP-first rate above the random null.

## Rules (fixed now; everything not listed is identical to 022)
- 1h context (ER20 ≥ 0.32 and slope of the 1h SMA20), 5m SMA20 and ATR14, stretch 2·ATR, target
  = 5m SMA20, window 07:00 NY → 16:00 London, flat 16:00 London: **as 022**.
- **A:** signal frame 1m; 1m sweep of the latest confirmed 1m swing (3 bars each side), exactly as
  022. **Stop = 1.5 × ATR14 of the last closed 5m bar**, from the signal close.
- **B:** signal frame **5m**. Stretch: the 5m bar's high ≥ its SMA20 + 2·ATR14 (low ≤ SMA20 −
  2·ATR14), using that bar's own SMA/ATR (known at its close). Swing: highest (lowest) of
  7 5m bars centred on it, usable only 3 bars later and only from the next bar on. Sweep:
  high > latest confirmed 5m swing high and close < it (mirror for longs). Entry next 5m open.
  **Stop = 1 pip beyond the 5m sweep bar's extreme.** Target = the 5m SMA20 at the signal bar;
  skip if price is already beyond it.
- Primary = "trending, stretch with the trend"; trend_against and sideways reported too.

## Evaluation (fixed now; as 022)
- Full suite; H1/H2; spread-adjusted null; context table.
- **Pass (dev year):** primary 95% CI excludes 0 AND both halves positive AND TP-first ≥ 2 SE
  above the null. A pass means "confirm on other years", nothing more.
- Comparison with 022's primary (−0.30 pips/trade, TP-first 16.4% vs 18.0%).
- Audits as 022 (sweep and stretch re-derived in plain Python on 1s-rebuilt bars, swings with
  their confirmation delay, on the signal timeframe); A: stop = 1.5 × 5m ATR checked.

## Results
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
