# 048 — London fade with the stop at the sweep candle + 3 pips, EURUSD 2023 only

**Date:** 2026-10-06 · file: research/strategies/048_london_fade_sweep_stop.py
**Status:** pre-registered (user request, after looking at trades in the viewer)

## What
046 unchanged except the stop: **short stop = sweep candle's high + 3 pips; long stop = sweep
candle's low − 3 pips** (distance = |signal-candle extreme − its mid close| + 3 pips, applied from the
fill). Target, entry, context, hours (03:00–04:59 NY, 1h sideways), flat 16:00 NY and the ±1 h news
blackout are the same.

## Compare with
046 on 2023: 199 trades, +263.5, +1.32/trade [CI +0.08, +2.64], median stop 7.0 / target 10.0,
target-first 49.2% vs 39.1% chance, fair Sharpe 1.87.

Prior evidence: in 022 a sweep stop with a 1-pip buffer (~2.8 pips) sat inside normal 1m noise and
lost; in 024 swing + 0.5 ATR buffer was worse than the ATR stop. Main things to look at: stop size,
win rate, and whether target-first beats the (stop-adjusted) chance rate by more or less than 046's +10 points.

## Results
_(filled after the run)_
