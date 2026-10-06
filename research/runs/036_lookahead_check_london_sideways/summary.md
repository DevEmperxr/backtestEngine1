# 036 — Lookahead checks for the London-open sideways slice (034/035)

**Date:** 2026-10-06 · script: research/regime/lookahead_check_034.py · raw: [results.json](results.json)
**Status:** done: no lookahead found

## Why
The user found the 035 result suspicious. Three checks.

## 1. Code review (022 strategy as used by 034)
- 1h context and 5m SMA/ATR: built from the 1m bars, joined **as-of backward on close_time**, so
  only bars closed at or before the signal bar's close are used.
- 1m swings: centred 7-bar max/min, shifted by 3 (confirmation) and then by 1 more, so a swing
  is usable only from the bar after its confirmation bar.
- Entry hour and context come from the signal bar; the engine enters at the next bar's open and
  resolves SL/TP on the 1s path.

## 2. Future-scramble test
Every 1m bar from 1 July onward replaced by a random walk at a different price level, then
signals regenerated. Before the cut-off, **0 differences** in every column (long/short signal,
sl, tp, context, swings, 5m MA/ATR, window, exit flag), for 2023 (187,188 rows, 2,316 signals)
and 2024 (185,932 rows, 2,211 signals). After the cut-off the signals changed (2,310 → 2,112 and
2,220 → 2,100), which shows the test is sensitive. **No signal depends on future prices.**

## 3. One-minute-late entry
Every signal moved one bar later (enter at t+2's open):

| slice | on time | 1 minute late |
|---|---|---|
| 2023 | 207 trades, +320.5, +1.55/trade | 200, +304.9, +1.52/trade |
| 2024 | 225, +140.0, +0.62/trade | 225, +249.1, +1.11/trade |

A delay doesn't kill it, so the result doesn't depend on an impossible fill at the exact
signal moment.

## Other reasons to be sceptical (not lookahead)
- **2024 depends on a few trades:** without its 5 best trades, 2024's +140 drops to **+32.9**
  (2023 without its best 5: +196.4).
- Ex-best-month: 2023 +207.2, 2024 +102.2.
- Exits: about half TP, half SL. Median stop 5–7 pips, target 8–10, spread 0.2–0.3 pips.
- It was found by slicing (034) and one year of test (035) only holds direction.

## Conclusion
No lookahead. The results are what the rules produce on real prices. What makes them
"sus" is statistical, not a leak: the edge was found by slicing, shrank on the test year, and
2024's profit rests on a handful of trades.
