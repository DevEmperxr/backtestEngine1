# 045 — Run 042 (two windows) with a ±1 h red-news blackout, EURUSD 2023 + 2024

**Date:** 2026-10-06 · file: research/strategies/045_two_windows_news_blackout.py
**Status:** done. Blackout NOT adopted (hurts the NY window, ~neutral for London)

## What
Exactly run 042 (Idea 1 rules; entries only 03:00–04:59 NY with the 1h sideways, or 08:00–09:59 NY
with the 1h trending), plus, for every ForexFactory High Impact (red) USD or EUR release:
- no new entries from **1 h before to 1 h after** the release time;
- any open trade is **closed 1 h before** the release (engine exit_signal, filled at that minute's open).

Days whose red event has no recoverable time (Powell speeches without a usual time, Euro summits,
elections: 12 days in 2023–2024) are blocked entirely.

## Release times (new: research/regime/news.py red_news_times)
The calendar stores about half of the red events with time 00:00. Recovered as the event's usual
home-zone clock time (New York for USD, Frankfurt for EUR) from rows that have one (2019–2025;
mostly 100% consistent once the file's clock offset is fixed: Iran's DST ended in 2022, so 2023+
rows are UTC+3:30 despite some +04:30 labels). For NFP, Unemployment Rate, Retail Sales, ECI,
German Flash Services PMI and German Prelim CPI, which never carry a time, the official release
times are used. Spot checks: NFP 2024-03-08 13:30 UTC, FOMC 2023-06-14 18:00 UTC, CPI 2024-04-10
12:30 UTC, ECB 2024-06-06 12:15 UTC: all correct. 588 timed releases in 2023–2024.

## What we compare
042 (all days) vs 044 (skip whole red days) vs 045 (±1 h blackout), per window and combined.
No prior expectation: 044 showed the profit sits on red days, but not when in the day.

## Results
Lookahead audit clean both years. Independent check: 0 trades open inside any blackout, 0 trades
on whole-day blocks. Comparison: research/regime/compare_045.py -> comparison.json.

| | London 042 | London 045 | NY 042 | NY 045 | Both 042 | Both 045 |
|---|---|---|---|---|---|---|
| trades | 434 | 409 | 157 | 97 | 591 | 506 |
| pips 2023 / 2024 | +322 / +140 | +264 / +192 | −25 / +158 | −45 / +59 | +298 / +298 | +219 / +251 |
| per trade (95% CI) | +1.07 [+0.25, +1.91] | +1.11 [+0.29, +1.92] | +0.85 [−0.94, +2.72] | +0.14 [−1.85, +2.22] | +1.01 [+0.21, +1.79] | +0.93 [+0.16, +1.70] |
| fair Sharpe | 1.75 | 1.81 | 0.64 | 0.11 | 1.77 | 1.69 |
| max DD (pips) | −147 | −131 | −122 | −136 | −126 | −104 |
| months positive | 16/24 | 15/24 | 16/24 | 12/24 | 19/24 | 17/24 |

(044, skipping whole red days: London +27, NY +77, both +104.)

- **London fade: about the same** (per trade +1.07 -> +1.11). Few red releases fall in 03:00–05:00 NY,
  so the blackout rarely touches it. Together with 044: the London fade earns on red-news *days*
  (busier days), not from the releases themselves.
- **NY open: much worse** (+133 -> +14). The 08:00–10:00 window sits on top of the 08:30 and 10:00 US
  releases, so the blackout removes 60 of its 157 trades, and those were its better trades. That
  matches 043 (08:30–09:00 entries positive both years) and the idea that the first move after a
  release often overshoots and partly comes back (Ederington & Lee 1995): the NY window seems to make
  its money fading post-release moves.
- Combined: a bit lower (+595 -> +469) with a slightly smaller drawdown.

Next idea worth testing (hypothesis, fixed before running, needs fresh data such as GBPUSD 2023+2024):
the opposite of a blackout for the NY window, i.e. only fade after a red US release.

