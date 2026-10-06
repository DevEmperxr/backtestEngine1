# 046 — London-open sideways fade on its own, with the news blackout, EURUSD 2023 + 2024

**Date:** 2026-10-06 · file: research/strategies/046_london_fade_standalone.py
**Status:** done. Current best EURUSD lead (in-sample)

## What
Idea 1 / 023A rules (1m sweep of the latest confirmed 1m swing after a 2x ATR stretch from the 5m
SMA20; stop 1.5 x 5m ATR; target the 5m SMA20), entries only **03:00–04:59 New York with the 1h
sideways** (ER20 < 0.32 or flat slope). Window 08:00 London -> 16:00 NY, flat 16:00 NY, one position
at a time. Standing rule: ±1 h red-news blackout (USD/EUR), open trades closed 1 h before a release.
No parameter changed from 034/035/045.

## Why
In 042/045 it shared one account with the NY window; on its own, no trade is blocked by an NY trade
(and vice versa), so this is its standalone record. Expect it close to its part of 045
(409 trades, +455.1, +1.11/trade).

## Status of the evidence
Found on 2023 (034), first test on 2024 (035, direction held). Still in-sample for the pair of years.
The real exam is 2021, 2022 and 2025 up to 2025-04-07 (news calendar end), only with the user's go-ahead.

## Results
Lookahead audit clean both years. Stats: research/regime/stats_046.py -> stats.json; charts
equity_monthly_2023_2024.png, trade_shapes.png. Identical to the London part of 045 (the NY window
never blocked a London trade).

| | 2023 + 2024 |
|---|---|
| trades | 409 (17 a month, on 276 of 522 weekdays) |
| net pips | **+455.1** (2023 +263.5, 2024 +191.6) |
| per trade (95% CI) | +1.11 [+0.29, +1.92] |
| win rate / avg win / avg loss | 48.9% / +9.1 / −6.5 (payoff 1.39), PF 1.33 |
| target hit first vs random-walk null | 49.2% vs 39.1% (2023), 48.5% vs 39.1% (2024) |
| median stop / target | 6.1 / 8.9 pips; median hold 28 min (90% within 113 min) |
| max drawdown | −130.6 pips (−1.3% at 1 pip = $1), longest underwater 308 days |
| fair Sharpe / Sortino (all weekdays) | 1.81 / 2.40 |
| months positive | 15/24; quarters positive 7/8 (only 2023-Q2 −46.6) |

Robustness:
- without best 5 / 10 trades: +335.6 / +239.6; 2024 alone without its best 5: +87.9
- double the spread cost: +351.4
- longs +335.3, shorts +119.8 (both positive); 03:xx entries +286.4, 04:xx +168.7 (both positive)
- caveat: 2023-Q4 alone is +199.5 (44% of the total); the other 7 quarters together are +255.6.

**Verdict:** positive in every main slice, beats chance on target hits in both years, survives doubled
costs. Still in-sample (found on 2023, 2024 was its first test). Next: the pre-registered final check on
the reserved years 2021, 2022 and 2025 up to 2025-04-07, only with the user's go-ahead.

