# 074 — Daily-trend bias + three different POIs (immediate entry), FTMO 1-step shape, EURUSD 2023 + 2024

**Date:** 2026-10-07 · strategy: research/strategies/074_trend_bias_pois.py · analysis: research/regime/trend_bias_074.py
**Status:** done. No candidate; all three negative in both years. User: "Keep the daily-trend bias and try a different POI or entry under it." In-sample.

## Kept from 073
- **Bias:** previous completed FX day's close vs its 50-day SMA (data/derived/eurusd_daily_2023_2024.parquet):
  up -> longs only, down -> shorts only. (The only layer that improved both years in 073.)
- **Execution:** entry at the next 1m open after the signal (no confirmation layer: it hurt in 047/053/073); stop =
  target = 1.5 × ATR(14) of the last closed 1h bar; one trade per New York day; signals 08:00 London -> 12:00 New York;
  flat 16:00 NY; FTMO ±2 min news; prop mode ($5/lot, flat by 16:55 NY). No context layer (dropped in 073).
- 2023 compared from 2023-03-13 (when the bias exists) for every variant.

## Three POIs (fixed now; no others will be tried on these years)
- **P1 sma_pullback:** last closed 1h close on the trend side of its SMA20, and a 1m bar touches the SMA20 (long: low ≤
  SMA20 in an uptrend; short: high ≥ SMA20 in a downtrend). Who loses: dip sellers expecting a reversal at value.
- **P2 donchian:** a 1m close beyond the highest high (uptrend) / lowest low (downtrend) of the last 20 closed 1h bars.
  Who loses: counter-trend traders whose stops sit beyond recent extremes (forced buying/selling).
- **P3 prev_day:** a 1m close beyond the previous FX day's high (uptrend) / low (downtrend). Who loses: the stop
  cluster at yesterday's extreme (060 found it a coin flip without a bias).

## Bar (stricter: three tries)
A POI is a **candidate** only if, after all FTMO costs: R per trade > 0 in **both** 2023 and 2024, pooled R per trade
**≥ +0.05**, and `ftmo_1step_scorecard` beats its zero-edge twin. **Strong:** also pooled bootstrap 95% CI above 0.
Reference: 073-B (RSI(2) dip + bias) pooled +0.009R.

## Results
All 6 runs: lookahead audit ok. Analysis: research/regime/trend_bias_074.py -> results.json; charts pois_equity.png,
equity_R_<p>.png. R after spread + $5 commission (costs ≈ 0.06R per trade).

| POI (+ daily-trend bias) | 2023 (from Mar 13): trades, R/trade | 2024: trades, R/trade | both: R/trade [CI] | FTMO 1-step pass / $ per attempt (twin) |
|---|---|---|---|---|
| P1 pullback to 1h SMA20 | 135, −0.111 | 155, −0.036 | −0.071 [−0.17, +0.03] | 9.7% / −$50 (32.3% / +$139) |
| P2 20-hour breakout | 95, −0.063 | 132, −0.149 | −0.113 [−0.23, +0.01] | 4.3% / −$78 (25.7% / +$80) |
| P3 previous-day break | 82, −0.016 | 100, −0.141 | −0.085 [−0.22, +0.06] | 6.8% / −$63 (23.7% / +$62) |
| *ref. 073-B RSI(2) dip* | *121, +0.099* | *156, −0.061* | *+0.009* | *36.0% / +$194 (31.5% / +$146)* |

**Verdict: no candidate.** All three lose in both years after costs, and all three are worse than their zero-edge
twins on the FTMO scorecard (they lose the fee on average). Before costs they are roughly flat to slightly negative.
- **Trend continuation (P2, P3) loses**: buying breakouts in the trend's direction doesn't pay at this scale, the
  same as plain breakouts in 059 (breakout traders are the losers at these times).
- **A calm pullback to the average (P1)** does worse than the sharp RSI(2) dip (073-B): the trend bias only seemed to
  help when combined with a sharp, oversold move.
- The daily-trend bias on its own doesn't create an edge; in 073 it improved a near-zero signal, nothing more.

