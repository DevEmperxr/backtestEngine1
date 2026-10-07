# 073 — "Buy the dip in the trend": RSI(2) pullback, built layer by layer for FTMO 1-step, EURUSD 2023 + 2024

**Date:** 2026-10-07 · strategy: research/strategies/073_trend_dip_rsi2.py · analysis: research/regime/trend_dip_073.py
**Status:** pre-registered. User: "develop a strategy that is indicator based that makes sense to you ... fit the
FTMO shape ... only use eurusd 2023 and 2024". In-sample by construction (no other years allowed); any pass is provisional.

## 0. Who loses, and why
Short-term traders who chase or panic into a sharp 1–2 hour move **against the day's trend** demand liquidity in a hurry;
whoever supplies it earns the snap-back. Short-term reversal profits are compensation for liquidity provision and are
larger when volatility is high (Nagel 2012, RFS). The classic indicator form is Connors' RSI(2) pullback in the direction
of the longer trend (buy oversold dips above the 200-day average); here adapted to FX intraday.

## Template (fixed now)
1. **Context:** active market = daily ATR(14) of the previous completed FX day above its 100-day median.
2. **Bias:** previous completed FX day's close vs its 50-day SMA (mid): above -> longs only; below -> shorts only.
3. **POI:** RSI(2) of the last closed **1h** bar ≤ 10 (long setup) or ≥ 90 (short setup); signal window 08:00 London ->
   12:00 New York, weekdays.
4. **Confirmation:** while the POI is active, the last closed **15m** candle closes beyond the previous 15m candle's high
   (long) / low (short).
5. **Execution:** entry at the next 1m open; stop = target = **1.5 × ATR(14) of the last closed 1h bar** (≈ 15 pips);
   one trade per New York day; flat 16:00 NY; FTMO ±2 min news rule; prop mode ($5/lot round trip, flat by 16:55 NY).
   Mid prices for indicators; 1m bars; FX day = 17:00–17:00 New York.

## Layer-by-layer plan (fixed now)
Variants: **A** = POI only (entry when the 1h RSI(2) extreme appears) · **B** = A + bias · **C** = B + context ·
**D** = C + confirmation. Order: add bias, then context, then confirmation. A layer is **kept** only if it raises
R per trade (after all costs) in **both** 2023 and 2024 versus the version without it; otherwise it is dropped and the
next layer is added to the version without it (e.g. if C fails, D = B + confirmation). Because of that branching,
the dropped-layer branches are pre-declared: **B'** = A + context, **D'** = B + confirmation, **D''** = A + confirmation.

## Warm-up (added before any result)
Daily indicators (SMA50, ATR14 and its 100-day median) are computed from EURUSD 2023+2024 joined
(data/derived/eurusd_daily_2023_2024.parquet), so 2024 is warmed up by late 2023; the bias exists from 2023-03-13 and
the context from 2023-04-13. **All layer comparisons for 2023 use trades from 2023-04-13 on, for every variant**, so
each layer is compared on the same days. No 2022 data is used.

## Final candidate and bar
The final kept version is scored with `lib.prop_firms.ftmo_1step_scorecard` (2023–24 trades) against its zero-edge twin.
**Candidate** = R per trade after costs > 0 in both years AND the scorecard beats the twin. Since everything is in-sample,
a candidate still needs a clean check on a year the user names.

## Results
_(filled after the run)_
