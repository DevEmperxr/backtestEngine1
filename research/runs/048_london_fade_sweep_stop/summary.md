# 048 — London fade with the stop at the sweep candle + 3 pips, EURUSD 2023 only

**Date:** 2026-10-06 · file: research/strategies/048_london_fade_sweep_stop.py
**Status:** done. Discarded (ATR stop stays)

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
Lookahead audit clean. Comparison: research/regime/compare_048.py -> comparison.json.

| 2023 | ATR stop (046) | sweep + 3 pips (048) |
|---|---|---|
| trades | 199 | 222 |
| net pips | +263.5 | +119.1 |
| per trade (95% CI) | +1.32 [+0.08, +2.64] | +0.54 [−0.47, +1.57] |
| win rate / PF | 49.2% / 1.35 | 36.9% / 1.17 |
| target hit first vs chance | 49.2% vs 39.1% (+10.2) | 36.7% vs 30.3% (+6.4) |
| stop size p10 / median / p90 | 5.2 / 7.0 / 10.4 | 3.7 / 4.7 / 6.9 |
| fair Sharpe | 1.87 | 0.98 |

Paired (193 entries taken by both): the new stop is tighter on 167. **24 trades that won in 046 are
stopped out in 048 (+266.7 -> −115.8); only 1 loser turns into a winner.** After the sweep, price
often pokes back a few pips past the sweep candle's extreme before snapping back to the average; a
stop just beyond the wick gets caught by that retest. The trade needs the wider ATR room, the same
lesson as 022/024. (More trades, 222 vs 199, because quicker stop-outs free the slot for later signals.)

