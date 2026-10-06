# 049 — London fade: sweep + 3 pip stop, break-even at +2R, target 4R, EURUSD 2023 only

**Date:** 2026-10-06 · file: research/strategies/049_london_fade_be2r_tp4r.py
**Status:** pre-registered (user request: "let our winners win")

## What
Entry as 046 (1m sweep after a 2x ATR stretch, 03:00–04:59 NY, 1h sideways, news blackout).
- Stop: sweep candle high/low ± 3 pips (as 048), R = that distance (median ~4.7 pips in 048).
- Break-even: once price has moved +2R in favour, the stop moves to the entry price (engine
  be_trigger_pips; resolved on the 1s path).
- Target: 4R from entry (replaces the 5m SMA20).
- Otherwise flat at 16:00 NY or 1 h before a red release.

## Compare with
046 (ATR stop, MA target): 199 trades, +263.5 · 048 (sweep+3 stop, MA target): 222, +119.1.
Prior evidence: in 032 price reached every distance (0.25–3R) before the stop at about chance rates,
so a bigger target alone shouldn't add edge; this checks it on the London fade with this stop.
Chance benchmark for a 4R target with a break-even rule is not the simple formula; compare net pips
and the R distribution with 048 on the same entries.

## Results
_(filled after the run)_
