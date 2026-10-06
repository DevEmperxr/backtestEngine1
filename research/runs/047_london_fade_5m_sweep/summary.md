# 047 — London fade with the sweep on 5m candles (vs 1m), EURUSD 2023 only

**Date:** 2026-10-06 · file: research/strategies/047_london_fade_5m_sweep.py
**Status:** pre-registered (user request: "see what would happen if we sweep on 5min too")

## What
046 unchanged except the trigger: the sweep is read on **5m candles**. A 5m candle must reach the
2 x ATR stretch line, poke past the latest confirmed 5m swing (extreme of 7 candles, confirmed 3
candles later, usable from the next candle), and close back inside. Entry at the next 5m candle's
open. Same 1h sideways context, entries 03:00–04:59 NY (signal candle close), stop 1.5 x 5m ATR14,
target the 5m SMA20 distance, flat 16:00 NY, ±1 h red-news blackout. Stops/targets still resolved
on the 1s path.

## Compare with
046 on 2023: 199 trades, +263.5 pips, +1.32/trade, target-first 49.2% vs 39.1% chance.
Expectation: far fewer trades (a 5m sweep at the stretch line is rarer); earlier, 023B (5m sweep,
whole-day window, any context) was discarded, but that was a different slice.

Year: **2023 only** (user's instruction for this change).

## Results
_(filled after the run)_
