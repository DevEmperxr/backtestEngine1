# 053 — London fade one timeframe up (4h context / 15m setup / 5m sweep), EURUSD 2023 only

**Date:** 2026-10-06 · file: research/strategies/053_london_fade_higher_tf.py
**Status:** pre-registered (user request; 2023 only for now)

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
_(filled after the run)_
