# 045 — Run 042 (two windows) with a ±1 h red-news blackout, EURUSD 2023 + 2024

**Date:** 2026-10-06 · file: research/strategies/045_two_windows_news_blackout.py
**Status:** pre-registered (user request)

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
_(filled after the run)_
