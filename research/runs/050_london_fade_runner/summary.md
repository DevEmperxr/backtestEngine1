# 050 — London fade: let a runner go past the middle band (B all-in, C half off), EURUSD 2023 only

**Date:** 2026-10-06 · file: research/strategies/050_london_fade_runner.py
**Status:** pre-registered (user chose "b and c")

## What
Entry and stop exactly as 046 (1m sweep after a 2x ATR stretch, 03:00–04:59 NY, 1h sideways,
stop 1.5 x 5m ATR, news blackout). Exits:
- **A (= 046, reference):** all out at the middle band (5m SMA20 distance at the signal).
- **B:** at the middle band the stop moves to break-even; target = the **opposite stretch band**
  (MA −/+ 2 x 5m ATR at the signal); anything still open is closed at **08:00 New York**.
- **C:** as B, but **half is closed at the middle band** (new engine partial take-profit) and the
  other half runs as in B.
All distances fixed at the signal candle, applied from the fill; resolved on the 1s path.

## Why / expectation
The edge we know is the snap-back to the average (target-first 49% vs 39% chance). Past the
average, a random walk would make B roughly break even against A (≈ +9.5 vs +10 pips on a
typical trade, with more variance); B/C only win if price on these choppy London mornings tends
to carry on to the other side of the range. Decision rule: adopt B or C only if it beats A on
2023 by more than noise AND then holds on 2024; otherwise keep "take profit at the middle band".

## Results
_(filled after the run)_
