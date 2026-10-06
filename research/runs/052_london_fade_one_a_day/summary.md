# 052 — London fade with at most one trade per day, EURUSD 2021–2024

**Date:** 2026-10-06 · file: research/strategies/052_london_fade_one_a_day.py
**Status:** done. Not adopted (helps only in the practice years)

## What
046 unchanged, plus: only the first entry signal of each New York calendar day is taken (after the
news blackout); later signals that day are ignored.

## Data caveat
Run on 2021–2024. 2023/2024 are practice years; 2021/2022 were already used for this strategy in 051,
so they are no longer unseen. This shows whether the rule helps consistently, not a clean test.

## Compare with 046 (net pips / trades)
2021 −3.0 / 229 · 2022 +107.5 / 205 · 2023 +263.5 / 199 · 2024 +191.6 / 210.
Decision rule: adopt only if per-trade AND drawdown improve in at least 3 of 4 years; otherwise keep 046.
Note from 033: first trades of the day were the "least bad" for Idea 1 overall (different slice).

## Results
Lookahead audit ok all years. Script: research/regime/compare_052.py -> comparison.json.

| year | 046 all trades | 052 one a day | 046's 2nd+ trades of the day |
|---|---|---|---|
| 2021 | 229 tr, −3.0, −0.01/tr, DD −162 | 139 tr, **−40.5**, −0.29/tr, DD −164 | 90 tr, +37.5 |
| 2022 | 205 tr, +107.5, +0.52/tr, DD −234 | 134 tr, **−24.8**, −0.19/tr, DD −244 | 71 tr, +132.3 |
| 2023 | 199 tr, +263.5, +1.32/tr, DD −131 | 136 tr, **+266.5**, +1.96/tr, DD −60 | 63 tr, −3.0 |
| 2024 | 210 tr, +191.6, +0.91/tr, DD −72 | 140 tr, **+162.5**, +1.16/tr, DD −47 | 70 tr, +29.1 |
| all 4 | 843 tr, +559.6, +0.66/tr [−0.03, +1.35], Sharpe 0.95 | 549 tr, +363.7, +0.66/tr [−0.15, +1.47], Sharpe 0.78 | |

Target hit first vs chance, one-a-day: 2021 40.2 vs 39.7, 2022 39.1 vs 38.5 (at chance), 2023 53.3 vs 39.4,
2024 50.4 vs 40.0.

**Verdict:** by the decision rule (per trade AND drawdown better in >= 3 of 4 years) it is not adopted:
better only in 2023 and 2024. In 2021–2022 the first trade of the day was at chance and the later
trades made the money (+170). Per trade over all 4 years is identical (+0.66); the rule just cuts the
number of trades by a third. The practice-year improvement doesn't carry over.

