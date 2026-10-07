# 057 — London fade (046, unchanged) on GBPUSD, 2023 + 2024

**Date:** 2026-10-07 · strategy: research/strategies/046_london_fade_standalone.py (no changes)
**Status:** done. **FAIL** after costs; small edge before costs, as on EURUSD

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
Lookahead audit ok both years. Comparison: research/regime/compare_057.py -> comparison.json.

| | trades | net pips | net / trade | **gross / trade** | spread / trade | target first vs chance |
|---|---|---|---|---|---|---|
| GBPUSD 2023 | 205 | −48.9 | −0.24 | **+0.64** | 0.88 | 38.4% vs 36.5% |
| GBPUSD 2024 | 215 | −18.1 | −0.08 | **+0.64** | 0.73 | 39.1% vs 36.3% |
| **GBPUSD 2023+24** | 420 | **−67.0** | −0.16 [CI −1.22, +0.89] | **+0.64** | 0.80 | |
| EURUSD 2021 (unseen) | 229 | −3.0 | −0.01 | +0.26 | 0.28 | 40.7% vs 38.5% |
| EURUSD 2022 (unseen) | 205 | +107.5 | +0.52 | +0.95 | 0.42 | 39.8% vs 37.4% |
| EURUSD 2023 | 199 | +263.5 | +1.32 | +1.62 | 0.30 | 49.2% vs 39.1% |
| EURUSD 2024 | 210 | +191.6 | +0.91 | +1.12 | 0.21 | 48.5% vs 39.1% |

GBPUSD max drawdown −227; median stop / target 8.1 / 12.0 pips.

**Verdict: FAIL** (pooled net < 0). But the pattern is consistent: before costs the fade makes about
+0.6 pips per trade on GBPUSD in both years, and price hits the target first 2–3 points more often than
chance, the same as on unseen EURUSD 2021–22 (and EURGBP before costs, 038). The effect looks **real but
small: roughly +0.3 to +1 pip per trade before costs**. The 2023–24 EURUSD numbers (+1.1 to +1.6) were the
lucky high end. GBPUSD's spread (~0.8 pips per trade, ~3× EURUSD) eats all of it.

**For the prop-firm goal:** an edge this size only survives where the total cost per trade is well under
~0.5 pips. With prop-firm commission (~0.5–0.7 pips per trade on top of spread) it would fail on EURUSD too.
The London fade is not a viable prop-firm strategy as it stands.

