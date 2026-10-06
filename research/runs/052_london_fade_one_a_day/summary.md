# 052 — London fade with at most one trade per day, EURUSD 2021–2024

**Date:** 2026-10-06 · file: research/strategies/052_london_fade_one_a_day.py
**Status:** pre-registered (user request: "1 trade a day and see if it changes the results")

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
_(filled after the run)_
