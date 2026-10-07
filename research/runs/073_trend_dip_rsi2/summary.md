# 073 — "Buy the dip in the trend": RSI(2) pullback, built layer by layer for FTMO 1-step, EURUSD 2023 + 2024

**Date:** 2026-10-07 · strategy: research/strategies/073_trend_dip_rsi2.py · analysis: research/regime/trend_dip_073.py
**Status:** done. Not a candidate (final version negative in 2024); about break-even after costs. User: "develop a strategy that is indicator based that makes sense to you ... fit the
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
All 14 runs: lookahead audit ok. Analysis: research/regime/trend_dip_073.py -> results.json; charts
layers_equity.png, equity_R_final.png. R after spread + $5 commission (costs ≈ 0.05–0.06R per trade on ~12–15 pip stops).

| version | 2023 (from Apr 13): trades, R/trade | 2024: trades, R/trade | win 2023 / 2024 |
|---|---|---|---|
| A POI only | 173, +0.071 | 234, −0.091 | 55.5% / 46.6% |
| **B + bias (daily trend)** | **121, +0.099** | **156, −0.061** | 58.7% / 49.4% |
| B' + context (no bias) | 51, +0.119 | 107, −0.044 | 56.9% / 48.6% |
| C + bias + context | 35, +0.022 | 66, −0.021 | 54.3% / 53.0% |
| D + bias + context + confirmation | 28, +0.011 | 56, −0.082 | 50.0% / 48.2% |
| D' + bias + confirmation | 105, +0.026 | 131, −0.067 | 53.3% / 48.1% |
| D'' + confirmation only | 160, −0.073 | 219, −0.142 | 48.1% / 45.2% |

**Layer walk (pre-registered rule):** bias **kept** (better in both years: +0.071 -> +0.099, −0.091 -> −0.061);
context **dropped** (C worse than B in 2023); confirmation **dropped** (D' worse than B in both years).
**Final version = B (RSI(2) dip in the daily trend):** 277 trades, +0.009R per trade after costs over both years
(2023 +0.099, 2024 −0.061).

**FTMO 1-step scorecard** (best risk 1% / 1%): pass 36.0% vs 31.5% for its zero-edge twin; +$194 vs +$146 per
attempt; ~69 trades (~112 trading days) to pass, ~89 trades (~143 days) until money received > fee.

**Verdict: not a candidate** (pre-registered bar needs R per trade > 0 in both years; 2024 is −0.061). Overall it is
about **break-even after FTMO costs**, which the FTMO convexity turns into a small positive value per attempt in this
model, but there's no demonstrated edge.

**What's useful:** the **daily-trend bias** improved results in both years, the first bias layer to do so in our
research (trades in the direction of the 50-day trend beat counter-trend ones). The 15m confirmation hurt every time
(it enters later, after part of the snap-back, as in 047/053), and the volatility context cut the sample without
helping consistently.

