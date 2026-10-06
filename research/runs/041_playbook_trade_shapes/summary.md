# 041 — EURUSD playbook: trade shapes and a fair Sharpe (2023 + 2024, in-sample)

**Date:** 2026-10-06 · script: research/regime/playbook_stats.py · chart: [trade_shapes.png](trade_shapes.png) · numbers: [stats.json](stats.json)
**Status:** done (descriptive)

## Change to lib
`lib/evaluate.py` gained `sharpe_all_days()` (with a test). `evaluate()`'s Sharpe uses only days
that had an exit, which inflates the ratio for strategies that trade on few days. The new function
counts every weekday (no-trade days = 0). Both are reported below.

## Results (per piece and combined; same in-sample caveat as 040)
| | Idea 2 (trend, 2R) | London-open sideways fade | Fix fade (018) | **Combined** |
|---|---|---|---|---|
| trades (per month) | 99 (4.1) | 432 (18.0) | 215 (9.0) | 746 (31.1) |
| win rate | 43.4% | 48.8% | 56.7% | 50.4% |
| avg win / avg loss (pips) | 14.0 / −9.4 | 9.2 / −6.7 | 12.0 / −11.2 | 10.7 / −8.3 |
| payoff ratio (avg win ÷ avg loss) | 1.48 | 1.37 | 1.07 | 1.29 |
| profit factor | 1.14 | 1.31 | 1.41 | 1.31 |
| expectancy (pips/trade) | +0.74 | +1.07 | +1.98 | +1.29 |
| average result in R | +0.13 | +0.20 | +0.12 | +0.17 |
| best / worst trade | +33.9 / −28.3 | +37.6 / −15.6 | +46.3 / −33.8 | +46.3 / −33.8 |
| median stop / target (pips) | 10.6 / 21.2 | 6.1 / 9.0 | 24.7 / 23.0 | 8.0 / 12.2 |
| exits: target / stop / time-signal | 23 / 38 / 38% | 49 / 51 / 0% | 23 / 13 / 64% | 38 / 38 / 24% |
| holding time median (90th pct) | 53 min (109) | 27 min (111) | 300 min (300) | 50 min (300) |
| max losing streak | 7 | 7 | 7 | 8 |
| max drawdown | −95.8 pips (−0.95%) | −146.8 (−1.45%) | −193.4 (−1.89%) | −196.2 (−1.78%) |
| longest time below a previous peak | 205 days | 272 days | 239 days | 135 days |
| months positive | 14/24 | 16/24 | 16/24 | 18/24 |
| Sharpe, traded days only (framework) | 0.89 | 2.34 | 2.18 | 2.53 |
| **Sharpe, all weekdays (fair)** | **0.37** | **1.74** | **1.39** | **2.24** |
| Sortino, all weekdays | 0.37 | 2.23 | 1.67 | 3.68 |
| days with trades | 92/522 | 292/522 | 215/522 | 411/522 |
| total | +72.9 | +460.4 | +426.1 | +959.4 |

(% figures assume a $10,000 account at $1 per pip; Sharpe doesn't depend on size.)

## Reading
- Three different trade shapes: Idea 2 = few, slower trades that need their 2R winners; the London
  fade = many quick small trades, half hit target and half stop; the fix fade = few long holds (most
  run to the 16:00 NY close) with a wide stop and a higher win rate.
- The fair Sharpe is lower than the framework's for every piece, most for the sparse Idea 2 (0.89 →
  0.37). The combination's fair Sharpe (2.24) is much higher than any piece's, because the pieces lose in
  different months. Longest underwater stretch: combined 135 days vs 205–272 for the pieces.
- All in-sample (pieces chosen on these years). These are shapes, not evidence.
