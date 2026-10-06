# 050 — London fade: let a runner go past the middle band (B all-in, C half off), EURUSD 2023 only

**Date:** 2026-10-06 · file: research/strategies/050_london_fade_runner.py
**Status:** done. Neither adopted: take profit at the middle band (A) stays

## What
Entry and stop exactly as 046 (1m sweep after a 2x ATR stretch, 03:00–04:59 NY, 1h sideways,
stop 1.5 x 5m ATR, news blackout). Exits:
- **A (= 046, reference):** all out at the middle band (5m SMA20 distance at the signal).
- **B:** at the middle band the stop moves to break-even; target = the **opposite stretch band**
  (MA −/+ 2 x 5m ATR at the signal); anything still open is closed at **08:00 New York**.
- **C:** as B, but **half is closed at the middle band** (new engine partial take-profit) and the
  other half runs as in B.
All distances fixed at the signal candle, applied from the fill; resolved on the 1s path.

## Why / expectation
The edge we know is the snap-back to the average (target-first 49% vs 39% chance). Past the
average, a random walk would make B roughly break even against A (≈ +9.5 vs +10 pips on a
typical trade, with more variance); B/C only win if price on these choppy London mornings tends
to carry on to the other side of the range. Decision rule: adopt B or C only if it beats A on
2023 by more than noise AND then holds on 2024; otherwise keep "take profit at the middle band".

## Results
Lookahead audit clean for B and C (incl. break-even exits at entry, ATR stops). A re-run after the
engine change: identical (+263.5). New engine feature: partial take-profit (8 new tests, 214 pass).
Comparison: research/regime/compare_050.py -> comparison.json.

| 2023 | A: all out at middle band | B: BE + runner | C: half off + runner |
|---|---|---|---|
| trades | 199 | 191 | 191 |
| net pips | **+263.5** | +205.4 | +210.7 |
| per trade (95% CI) | +1.32 [+0.08, +2.64] | +1.08 [−0.45, +2.68] | +1.10 [−0.27, +2.49] |
| win rate / PF | 49.2% / 1.35 | 33.0% / 1.28 | 48.7% / 1.29 |
| max drawdown | **−130.6** | −164.9 | −146.8 |
| months positive | 6/12 | 7/12 | 7/12 |
| fair Sharpe | **1.87** | 1.33 | 1.52 |
| without best 10 | **+71.8** | −43.0 | +11.5 |
| median hold | 29 min | 52 min | 52 min |
| exits target / BE / stop / 08:00 | 97 / 0 / 100 / 2 | 37 / 30 / 97 / 27 | same as B |

**What happens after the middle band** (91 trades where A took profit, same entries in B): 37 went
on to the opposite band, 30 came back to break-even, 24 were closed at 08:00. Running them made
+922.1 vs +948.3 for just taking the profit: **no extra edge past the average**, exactly the
random-walk expectation in the plan. The runner adds holding time and swings, not pips.

**Verdict:** take profit at the middle band (A). Matches 032 (no exit adds edge beyond what the entry
gives) and the logic of the trade (the edge is the snap-back to the average).

