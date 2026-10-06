# 049 — London fade: sweep + 3 pip stop, break-even at +2R, target 4R, EURUSD 2023 only

**Date:** 2026-10-06 · file: research/strategies/049_london_fade_be2r_tp4r.py
**Status:** done. A real alternative to 046 (similar total, different shape); not yet preferred

## What
Entry as 046 (1m sweep after a 2x ATR stretch, 03:00–04:59 NY, 1h sideways, news blackout).
- Stop: sweep candle high/low ± 3 pips (as 048), R = that distance (median ~4.7 pips in 048).
- Break-even: once price has moved +2R in favour, the stop moves to the entry price (engine
  be_trigger_pips; resolved on the 1s path).
- Target: 4R from entry (replaces the 5m SMA20).
- Otherwise flat at 16:00 NY or 1 h before a red release.

## Compare with
046 (ATR stop, MA target): 199 trades, +263.5 · 048 (sweep+3 stop, MA target): 222, +119.1.
Prior evidence: in 032 price reached every distance (0.25–3R) before the stop at about chance rates,
so a bigger target alone shouldn't add edge; this checks it on the London fade with this stop.
Chance benchmark for a 4R target with a break-even rule is not the simple formula; compare net pips
and the R distribution with 048 on the same entries.

## Results
Lookahead audit clean (incl. every break-even exit exactly at entry). Comparison:
research/regime/compare_049.py -> comparison.json.

| 2023 | 046 ATR stop, MA target | 048 sweep+3, MA target | 049 sweep+3, BE 2R, TP 4R |
|---|---|---|---|
| trades | 199 | 222 | 212 |
| net pips | +263.5 | +119.1 | **+232.7** |
| per trade (95% CI) | +1.32 [+0.08, +2.64] | +0.54 [−0.47, +1.57] | +1.10 [−0.21, +2.47] |
| win rate / PF | 49.2% / 1.35 | 36.9% / 1.17 | 23.1% / 1.36 |
| exits target / BE / stop / time | 97 / 0 / 100 / 2 | 81 / 0 / 140 / 1 | 40 / 37 / 126 / 9 |
| median stop / target (pips) | 7.0 / 10.0 | 4.7 / 10.8 | 4.7 / 18.8 |
| max drawdown | −130.6 | −118.9 | **−86.8** |
| max losing streak | 7 | – | 9 |
| months positive | 6/12 | 6/12 | **8/12** |
| H1 / H2 | +10.8 / +252.7 | +8.5 / +110.6 | **+110.3 / +122.4** |
| fair Sharpe | 1.87 | 0.98 | 1.58 |
| without best 5 / best 10 | +153.1 / +71.8 | +20.4 / −57.4 | +84.3 / **−38.7** |

On the same 211 entries, BE 2R + TP 4R turned 048's +108.0 into +232.7: letting winners run more
than makes up for the tight stop. Versus 046 the total is similar, but the shape differs:
- better: smoother (both halves equal), smaller drawdown, more positive months
- worse: 23% win rate (77% of trades lose or scratch), CI includes 0, and the result rests on the
  big winners (without the best 10 trades it's negative; 046 stays positive).

Caveat: 4R/2R were the user's choice and only one setting was tested (good: no tuning), but on
2023 alone. Comparing 046 vs 049 fairly needs 2024 (practice year), with both rules fixed as they are.

