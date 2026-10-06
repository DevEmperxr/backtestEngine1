# 053 — London fade one timeframe up (4h context / 15m setup / 5m sweep), EURUSD 2023 only

**Date:** 2026-10-06 · file: research/strategies/053_london_fade_higher_tf.py
**Status:** done. Discarded (no edge on 2023)

## What
| part | 046 | 053 |
|---|---|---|
| context ("sideways" = ER20 < 0.32) | 1h | **4h** |
| stretch (SMA20 ± 2×ATR14), stop (1.5×ATR), target (SMA20) | 5m | **15m** |
| sweep trigger (latest confirmed swing, k = 3) and entry (next bar open) | 1m | **5m** |

Unchanged: entries 03:00–04:59 NY, ER threshold 0.32 (calibrated on 1h, kept as instructed), window
08:00 London -> 16:00 NY (flat 16:00 NY), ±1 h news blackout, one position at a time, no daily limit.
New strategy settings: setup_min / ctx_min (defaults 5 / 60 keep every earlier run identical; 046 and
047 rechecked: +263.5 and +19.2, audits ok). The audit now builds setup candles at setup_min.

## Expectation / compare with
046 on 2023: 199 trades, +263.5, +1.32/trade. Expect far fewer trades (a 5m sweep at a 15m 2×ATR stretch
inside a 2-hour window is rare) and wider stops/targets (15m ATR is about 1.7x the 5m ATR). Small sample:
judge per-trade and target-first vs chance, not just the total.

## Results
Lookahead audit ok (incl. 15m stretch and ATR stops). Comparison: research/regime/compare_053.py.

| 2023 | 046 (1h / 5m / 1m) | 053 (4h / 15m / 5m) |
|---|---|---|
| trades | 199 | 90 |
| net pips | +263.5 | **−37.8** |
| per trade (95% CI) | +1.32 [+0.08, +2.64] | −0.42 [−2.63, +1.94] |
| win rate / PF | 49.2% / 1.35 | 42.2% / 0.92 |
| target hit first vs chance | 49.2% vs 39.1% | **41.5% vs 43.4% (below chance)** |
| median stop / target | 7.0 / 10.0 | 8.9 / 10.9 |
| median hold | 29 min | 36 min |
| fair Sharpe | 1.87 | −0.35 |
| H1 / H2 | +10.8 / +252.7 | +2.0 / −39.8 |

No sign of an edge: target-first is below the chance rate. As in 047 (5m sweep), waiting for a 5m
candle to close uses up much of the snap-back, so the target is barely bigger than the stop (10.9 vs
8.9 pips) even though the 15m bands are wider. The pattern seems to live in the fast 1m reaction at the
London open, not in a slower version of it.

