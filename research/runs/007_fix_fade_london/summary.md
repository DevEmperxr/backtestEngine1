# 007 — Fade the run-up into the 16:00 London fix, hold to 16:00 New York

**Date:** 2026-10-05
**File:** research/strategies/007_fix_fade_london.py
**Status:** exploring

## Hypothesis
*(written and committed before any code or backtest — pre-registration; 007–009 registered together)*

Krohn, Mueller & Whelan (JF 2024): around the major FX fixes, dealers hedge inventory
before the fix and unwind after it. Their conditional result: the return in the last
hour before a fix predicts the following window's return with a **negative** sign.
So: take the opposite side of EURUSD's 15:00→16:00 London move at the 16:00 London
(WM/R) fix and hold into the US afternoon.

**Contamination warning:** run 006 already showed, on this 2024 data, that trades open
at the London close tended to reverse afterwards (seen post hoc). This test checks
the mechanics and costs of a published effect. **It is not independent confirmation**,
whatever the result. Confirmation needs other years.

**Power warning:** the fix→16:00 NY move has SD ≈ 18.2 pips (2024, measured before this
registration, mean not looked at). One year gives a ±2.2-pip 95% CI on the daily
mean. The paper's unconditional EUR effect (~0.3 pips/day) is undetectable here; only
a much larger conditional effect could show.

## Rules (fixed in advance)
- 1m bars, mid prices. Signal bar = the 1m bar with close_time 16:00 Europe/London, Mon–Fri.
- r = mid close at 16:00 London − mid close at 15:00 London (close of the bar with
  close_time 15:00). r < 0 → **long** EURUSD; r > 0 → **short**; r = 0 → no trade.
- entry at the next 1m open (16:00:00 London); one trade per day.
- exit: force-flat at **16:00 America/New_York** (not 17:00: rollover spread, see 006).
- SL 50 / TP 50 pips: a disaster stop only (~2.7 SD), not part of the idea.

## Pre-registered evaluation plan
- full adversarial suite; H1/H2; gross expectancy vs 0; spread-adjusted null on any
  SL/TP-resolved trades; split by |r| above/below its median (descriptive).
- independent audit: rebuild 1m bars from 1s, recompute r with separate code, confirm
  trade direction = −sign(r), entry at 16:00 London, exit ≤ 16:00 NY.
- **raised bar (trial 7 on 2024):** candidate only if the expectancy CI excludes 0 AND
  both halves positive. Even then, "candidate pending out-of-sample data", given the
  contamination above.

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

