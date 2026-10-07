# 075 — Gold (XAUUSD): RSI(2) dip and 20-hour breakout in the daily trend, FTMO 1-step shape, 2023 + 2024

**Date:** 2026-10-07 · strategy: research/strategies/075_gold_trend_bias.py · analysis: research/regime/gold_075.py
**Status:** done. No candidate; gold isn't easier than EURUSD for these setups. User: "add gold support ... build some strat and test only on the two years". In-sample.

## Setup
- Gold support: pip = 0.1 ($10 per pip per 100 oz lot), FTMO gold commission 0.0007% of notional per side
  (`lib.prop.FTMO_GOLD`), Dukascopy bid/ask spread (median $0.38 in 2024). Daily features from XAUUSD 2023+2024 joined
  (data/derived/xauusd_daily_2023_2024.parquet); bias from 2023-03-14; all variants compared from that date.
- Rules carried over **unchanged** from EURUSD (no gold-specific tuning): signals 08:00 London -> 12:00 New York;
  entry at the next 1m open; stop = target = 1.5 × ATR(14) of the last closed 1h bar; one trade per NY day; flat 16:00
  NY; FTMO ±2 min news (USD); prop mode (flat by 16:55 NY).

## Ideas (fixed now)
- **G1 RSI(2) dip in the daily trend** (073-B): 1h RSI(2) ≤ 10 in an uptrend -> long; ≥ 90 in a downtrend -> short.
  Who loses: traders who chase/panic into sharp moves against the trend (liquidity demanders).
- **G2 20-hour breakout in the daily trend** (074-P2): 1m close beyond the 20 closed 1h bars' high (uptrend) / low
  (downtrend). Who loses: counter-trend traders whose stops sit beyond recent extremes. Gold trends more than EURUSD.
- **Drift check (reference, not a strategy):** enter in the daily trend's direction at the first minute after 08:00
  London every day, same stop/target. Gold rose ~$1,985 -> ~$2,790 over 2023–24, so with-trend longs can look good
  from drift alone.

## Bar (two ideas)
An idea is a **candidate** only if, after all FTMO costs: R per trade > 0 in **both** years; pooled R per trade
≥ +0.05; it beats the **drift check**'s R per trade; and `ftmo_1step_scorecard` beats its zero-edge twin.
Long and short trades reported separately.

## Results
All 6 runs: lookahead audit ok (after a bug fix before results: no signal until the 1h ATR exists). Analysis:
research/regime/gold_075.py -> results.json, gold_equity.png. R after spread + FTMO gold commission (costs ≈ 0.07–0.08R;
median stops ~$5–6 = 50–60 pips at pip 0.1).

| idea (from 2023-03-14) | 2023 R/trade | 2024 R/trade | both [CI] | before costs | long | short | FTMO 1-step pass / $ (twin) |
|---|---|---|---|---|---|---|---|
| G1 RSI(2) dip in trend | −0.166 | −0.198 | −0.183 [−0.29, −0.08] | −0.114 | −0.222 | −0.118 | 1.2% / −$87 (31% / +$133) |
| G2 20-hour breakout in trend | −0.128 | −0.043 | −0.083 [−0.20, +0.03] | −0.008 | +0.017 | −0.298 | 6.4% / −$71 (26% / +$80) |
| drift check (with-trend at 08:00 London) | −0.148 | −0.040 | −0.088 [−0.18, −0.00] | −0.011 | −0.024 | −0.219 | — |

**Verdict: no candidate.**
- **Buying dips in gold loses even before costs** (−0.11R), the opposite of EURUSD, where the sharp-dip version was the
  best (073-B ≈ 0). In gold, sharp moves against the trend tend to keep going rather than snap back.
- **The 20-hour breakout is flat before costs** (−0.01R) and loses the ~0.08R of costs; it's no better than the
  naive drift check, so it isn't adding anything.
- **Gold's 2023–24 rise didn't show up in the London/NY trading window:** even with-trend longs at 08:00 London were
  about flat (−0.02R after costs). Shorts on down-trend days lost clearly in all three (bull market).
- Costs relative to the trade size are a bit higher than EURUSD's (~0.075R vs ~0.06R).

