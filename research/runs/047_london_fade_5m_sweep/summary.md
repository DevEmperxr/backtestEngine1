# 047 — London fade with the sweep on 5m candles (vs 1m), EURUSD 2023 only

**Date:** 2026-10-06 · file: research/strategies/047_london_fade_5m_sweep.py
**Status:** done. Discarded (1m sweep stays)

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
Lookahead audit clean (after an audit fix: in 5m mode the audit now builds 5m candles the same way
the strategy does, from 1s; the first pass flagged 31 stops differing by at most 0.23 pips, purely
from the two ways of building candles). Comparison: research/regime/compare_047.py -> comparison.json.

| 2023 | 1m sweep (046) | 5m sweep (047) |
|---|---|---|
| trades | 199 | 99 |
| net pips | +263.5 | +19.2 |
| per trade (95% CI) | +1.32 [+0.08, +2.64] | +0.19 [−1.24, +1.68] |
| win rate / PF | 49.2% / 1.35 | 52.5% / 1.06 |
| target hit first vs chance | 49.2% vs 39.1% (+10 pts) | 52.5% vs 49.3% (+3 pts) |
| median stop / target | 7.0 / 10.0 | 6.8 / 6.6 |
| median hold | 29 min | 16 min |
| max DD | −130.6 | −101.1 |
| fair Sharpe | 1.87 | 0.26 |
| H1 / H2 | +10.8 / +252.7 | −18.3 / +37.5 |

Overlap: 27 of the 99 5m trades enter within 5 min of a 1m trade (−34.7 pips); the 72 others +53.9.

**Why it's worse:** waiting for the 5m candle to close means part of the snap-back has already happened
by entry. The stop stays the same (1.5 x ATR) but the distance left to the average shrinks (median
target 10 -> 6.6 pips), so the trade becomes ~1:1 and the edge over chance falls from +10 to +3 points.
The quick 1m reaction is what makes the London fade work.

