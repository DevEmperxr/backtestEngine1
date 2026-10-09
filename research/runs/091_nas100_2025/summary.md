# 091 — NAS100 noise-area momentum (079 rules, frozen) on 2025: the out-of-sample test

**Date:** 2026-10-09 · strategy: research/strategies/089_noise_area_indices.py `make_nas100_2025` · analysis:
research/regime/nas2025_091.py
**Status:** pre-registered BEFORE any 2025 price data is used. User: "ok test on 2025 now just nasdaq" (2025 named
explicitly; reserved year; first and only use for this idea). 2026 untouched.

## Rules: exactly 079 (reproduced by 089:nas100)
Cash session 09:30–16:00 NY; sigma per minute of session = 14-session average |price/open − 1|; Upper =
max(open, prev close)×(1+sigma), Lower = min(...)×(1−sigma); checks 10:00 … 15:30 every 30 min: long above, short
below, flat inside, flips reverse; stop one noise width; flat 15:55; FTMO index costs (no commission, +0.2 pt spread).
Only data change: the noise table is built from 2024+2025 joined so January 2025 is warmed up by December 2024.

## News (USD red, ±2 min)
- 1 Jan – 7 Apr 2025: ForexFactory file (as before).
- 8 Apr – 31 Dec 2025: rebuilt from official schedules (research/regime/news_rebuild.py): ISM Manufacturing / Services,
  JOLTS (BLS actual dates incl. the shutdown), FOMC statement / SEP / press conference / minutes, Powell testimony;
  Powell policy-speech days (16 Apr, 22 Aug, 23 Sep, 14 Oct) blocked all day (time not published). Validated 99/99 exact
  against ForexFactory for 2024 – Apr 2025 (news_rebuild_check.py).
- Known gap: "President Trump Speaks" (red on ForexFactory from 2025, irregular times) cannot be rebuilt after 7 Apr.

## Pass (same bar as the 079 candidate)
After all FTMO costs, 2025: **R per trade ≥ +0.05**, and the FTMO 1-step scorecard (2025 trades) beats its zero-edge
twin. Reported too: H1 / H2 2025, long vs short, the always-long twin (direction check from 089), before-cost result.
- Sensitivity A (reported): Jan – Apr 2025 with ForexFactory news minus the Trump-speech events, vs with them -> size of
  the post-April gap.
- Sensitivity B (reported): R of the trades open at 10:00 on CB Consumer Confidence days (last Tuesday) and Michigan
  preliminary days (2nd Friday) after 7 Apr, which ForexFactory sometimes marks red.
The verdict follows the main run; a sensitivity only changes it if it flips the sign of R per trade.

## Results
_(filled after the run)_
