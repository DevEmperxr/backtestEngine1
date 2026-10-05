# 008 — Fade touches of 50-pip round numbers (Osler)

**Date:** 2026-10-05
**File:** research/strategies/008_round_number_fade.py
**Status:** exploring

## Hypothesis
*(written and committed before any code or backtest — pre-registration; 007–009 registered together)*

Osler (2003, JF; NY Fed SR 125): take-profit orders cluster at round numbers, which is
why trends tend to stall and reverse at them. Stop-loss orders cluster just beyond them,
which is why a clean break accelerates. A 1m bar that **reaches a 50-pip level and
closes back on the side it came from** shows the take-profit liquidity absorbing the
move. Fading it, with the stop placed beyond the level, should win more often than a
random entry with the same bracket.

**Prior:** sceptical, but this has a documented order-flow mechanism, and nothing in this
project has tested round numbers yet.

## Rules (fixed in advance)
- 1m bars, mid prices; levels every 50 pips (x.xx00 and x.xx50).
- short signal: bar opens below a level L, its high ≥ L, and it closes < L (touch from below,
  rejected). long signal: opens above L, low ≤ L, closes > L. (If one bar would give
  both, skip it.)
- entry window and force-flat: entry time (= signal bar close_time) in [07:00 NY,
  16:00 London), Mon–Fri; flat at 16:00 London.
- entry at the next 1m open; ; one position at a time.
- **SL** at L ± 4 pips beyond the level (4 = 2.5 × median 1m ATR in the window, the
  rule used in 004): sl_pips = |signal close − (L ± 4 pips)| / pip.
- **TP** = 1.5 × sl_pips.

## Pre-registered evaluation plan
- full adversarial suite; H1/H2; spread-adjusted random-walk null; split by level type
  (x.xx00 vs x.xx50, descriptive: Osler finds clustering strongest at 00).
- independent audit: rebuild 1m bars from 1s; confirm every signal bar has a 50-pip
  level strictly between open and the extreme on the traded side and closed back.
- **raised bar (trial 8 on 2024):** CI excludes 0 AND both halves positive AND TP rate
  ≥ 2 SE above the spread-adjusted null.

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

