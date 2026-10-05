# 018 — Fade the day's opening-range breakout at the 16:00 London fix, out of sample

**Date:** 2026-10-05
**File:** research/strategies/018_orb_fix_fade.py
**Status:** exploring

## Hypothesis
*(registered before the 2023/2025 files were read: downloads still running, partial
files unopened)*

On 2024, 005's ORB trades still open at 16:00 London went on to lose −368.7 pips
(118 trades, −3.12/trade) by their exit (≤ 16:00 NY). Fading that leg would have made
+368.7 before ~25 pips of extra spread: 95% CI [+0.81, +5.50] pips/trade, positive in both
halves. This is the only 2024 result whose CI excludes zero. **It was found by looking**
(post hoc, after ~15 trials), so 2024 proves nothing. The mechanism is published: the
day's move tends to reverse after the London fix (Krohn, Mueller & Whelan 2024; Evans
2018). If real, it must show up in 2023 and 2025.

## Rules (fixed now)
- Run the **005 breakout unchanged** each day (07:00–08:30 NY range; first 1m mid close
  beyond it after 08:30 NY; entry next 1m open; SL at the opposite side from the signal
  close; TP = 1.5 × range).
- Determine, from 1m bid/ask highs and lows up to the bar closing 16:00 London, whether that
  breakout trade has touched its SL or TP. (A 1m bar's high/low contains every second's,
  so "touched before 16:00" is exact.)
- **If still open:** signal on the bar closing 16:00 Europe/London, Mon–Fri, in the
  **opposite** direction; entry at the next 1m open (16:00:00 London).
- Exits: **TP at the breakout's SL level, SL at the breakout's TP level** (distances measured
  from the signal-bar mid close; skip the day if either distance is ≤ 0), and force-flat at
  **16:00 New York**. This mirrors the leg measured in 2024.
- One trade per day max.

## Test design (fixed now)
- Test years **2023 and 2025**; 2024 = discovery reference only.
- **Criterion:** pooled 2023+2025 expectancy CI excludes 0 **and** net positive in both
  years. **Family:** 016A, 016B, 017A, 017B, 018. Family-level confirmation at **99%**
  (Bonferroni 0.05/5).
- Power: ~120 trades/year → ~240 pooled; SD ≈ 13 pips/trade (2024 leg) → SE ≈ 0.85.
  2024's +3.1/trade would be clearly visible if it persisted at even half that size;
  an effect ≤ ~1.5/trade would likely not confirm.
- **Independent audit:** run the 005 strategy through `Engine` on the same data (separate
  code path). Every 018 trade must sit on a day where 005's trade exited `exit_signal` at
  16:00 London, with the opposite direction, entry_time = that exit time, and the fade's
  TP/SL levels equal to the breakout's SL/TP levels (within distance-measurement rounding).

## Results — 2023
_(filled after the run)_

## Results — 2025
_(filled after the run)_

## Pooled 2023 + 2025 and 2024 reference
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
