# 057 — London fade (046, unchanged) on GBPUSD, 2023 + 2024

**Date:** 2026-10-07 · strategy: research/strategies/046_london_fade_standalone.py (no changes)
**Status:** pre-registered (user request)

## Why
The London fade was found on EURUSD 2023; on unseen EURUSD 2021–22 its edge shrank to +0.24 pips/trade
(051). A real effect should also show on another liquid, low-cost pair that is active at the London open.
GBPUSD has never been used for any strategy (fresh data).

## Setup
- Data: GBPUSD 1s 2023 and 2024 (Dukascopy, downloaded by the user with download_gbpusd.py).
- Rules exactly as 046: 1m sweep after a 2×ATR stretch from the 5m SMA20, entries 03:00–04:59 NY, 1h
  "sideways" (ER20 < 0.32, threshold kept from EURUSD), stop 1.5 × 5m ATR, target the 5m SMA20, flat 16:00 NY.
- News blackout: ±1 h around red **GBP and USD** releases (run_experiment sets the pair's currencies;
  GBP official times added for the BoE decision and fixed-time UK data).
- Costs: Dukascopy bid/ask as in all runs (no commission, as before).

## Pass bar (fixed now)
On 2023 + 2024 pooled:
- **PASS:** net pips > 0 AND target hit first more often than the spread-adjusted random-walk chance rate in
  BOTH years.
- **STRONG PASS:** PASS and the pooled 95% bootstrap CI of per-trade pips above 0.
- **FAIL:** otherwise.
Also reported: each year, gross vs net (spread share), per-trade, drawdown, stop/target sizes, EURUSD comparison.

## Results
_(filled after the run)_
