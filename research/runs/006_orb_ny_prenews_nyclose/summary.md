# 006 — ORB as 005, but the window and force-flat move to 16:00 New York

**Date:** 2026-10-05
**File:** research/strategies/006_orb_ny_prenews_nyclose.py
**Status:** exploring

## Hypothesis
*(written and committed before any code or backtest — pre-registration)*

Same idea as 005: a break of the pre-news 07:00–08:30 NY range carries US-session
momentum. In 005, 46% of trades were force-closed at 16:00 London (11:00 NY in
summer, 11:00/12:00 otherwise) before reaching SL or TP, so the test mostly measured
the first 2.5–3.5 hours. Extending the window to the 16:00 New York close gives each
breakout the whole US session (7.5 h) to reach a 1.5×-range target. If the breakout
has directional information that plays out slowly, it should show up here.

**Honest status: this is a data-informed variant.** The change was suggested by a
result of 005 (the time-exit share), on the same 2024 data. It is trial 6 on this year
(trial 2 of the ORB line), and it gets a correspondingly higher bar (below).

**Prior:** sceptical. 005's TP-first rate was at or below the random null on the
trades that did resolve, which suggests more time mostly converts time-exits into a
coin flip.

## Rules (fixed in advance; identical to 005 except where marked)
- 1m bars, mid prices; range 07:00–08:30 NY, ≥ 90 bars or day skipped
- breakout: first 1m mid close beyond the range with close_time in
  (08:30 NY, **16:00 New York**), one trade per day, entry at the next 1m open
- SL at the opposite side of the range from the signal close; TP = 1.5 × range height
- **force-flat at 16:00 New York** (was 16:00 London). The FX 17:00 NY close was
  rejected before running: the median spread is 1.5 pips at 17:00 vs 0.2 at 16:00
  (2024 1m data), so a forced exit there would mostly measure the rollover spread spike.

## Pre-registered evaluation plan
Same as 005 (full adversarial suite, H1/H2, spread-adjusted null, NFP/CPI split,
independent ORB audit, force-flat check now against 16:00 NY), plus:
- **direct comparison to 005**: the same days' trades; how did the 005 time-exited
  trades end with the extra hours?
- **raised bar (multiple testing):** with 6 trials on one year, call it a candidate
  only if the expectancy CI excludes zero **and** both halves are positive **and** the
  TP-first rate beats the spread-adjusted null by ≥ 2 standard errors. Otherwise discard.

## Headline result
_(filled after the run)_

## Adversarial checks
_(filled after the run)_

## Visual check
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
