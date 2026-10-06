# 043 — What separates good and bad NY-window trades? (descriptive, EURUSD 2023+2024)

**Date:** 2026-10-06 · script: research/regime/ny_window_diag_043.py · tables: tables.md
**Status:** diagnostic only (no rule changed). Source: the 157 NY-window trades of run 042.

Splits checked: half hour of entry, direction, red-news day (USD/EUR), 1st/2nd/3rd NY trade of the
day, whether the London window already traded that day, stop size, target/stop ratio, weekday.
That's ~27 groups, so a few will agree across both years by chance. Treat this as hypotheses only.

Groups positive in BOTH years:
- entry 08:30–08:59 (US data release time): 27 trades, +28.6 / +38.4
- a London-window trade already happened that day: 67 trades, +41.7 / +104.2 (other days −66.1 / +53.3)
- 2nd or later NY trade of the day: 50 trades, +16.3 / +87.1 (1st trade −40.8 / +70.4)
- target at least 2× the stop: 48 trades, +58.0 / +33.1 (target < 1.2× stop: −19.5 overall)
- (Wednesday: positive both years; no reason to expect it, ignored)

Not useful: direction, red-news day, stop size (signs flip between years).

**Takeaway:** nothing is strong. The main problem is 2023's 09:00–10:00 trades (−70 pips), which made
+128 in 2024. Any filter chosen from this table is fitted to these same 157 trades, so it needs a
fresh test. Since the NY window is about the US session, the fair fresh test is a USD pair (e.g.
GBPUSD 2023+2024, not downloaded yet), with the filter fixed before running.
