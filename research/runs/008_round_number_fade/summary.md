# 008 — Fade touches of 50-pip round numbers (Osler)

**Date:** 2026-10-05
**File:** research/strategies/008_round_number_fade.py
**Status:** discarded

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
- entry at the next 1m open; `exit_on_opposite_signal = False`; one position at a time.
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
- trades: 378 (from 1,007 in-window rejections; the rest fired while a trade was open),
  win rate 36.2%, net pips: **−181.7** (expectancy −0.48/trade)
- profit factor 0.85, avg win +7.5 / avg loss −5.0, max DD −2.8%, Sharpe −1.79
- exits: 129 TP / 232 SL / 17 force-flat
- verdict: `unprofitable`

## Adversarial checks
- gross vs net: gross **−91.8**, spread 89.9 → "no edge — gross P&L not positive".
- bootstrap CI (expectancy): **[−1.14, +0.19]**, mostly negative.
- MC drawdown: observed −2.77% vs median −2.38%, rank 16% → not fragile.
- ex-best-month: drop Jan (+79.5) → −261.2; ex top 5% → −410.4.
- **H1/H2:** H1 −20.1, H2 −161.6. Negative in both.
- **random-walk null (spread-adjusted):** TP-first 35.7% vs 38.0% (z ≈ −0.9).
- **Pre-registered level split:** x.xx00 levels 202 trades **−142.5** (win 33.7%); x.xx50
  levels 176 trades −39.2 (win 39.2%). Osler finds take-profit clustering strongest at
  00, so fading should work *best* there. It worked *worst*.
- **Raised bar:** no on all three counts.
- **lookahead audit: passed.** 378/378 entries verified; independent level scan on
  1s-rebuilt bars: 0 invalid signal bars; 0 SL mismatches; 0 force-flat violations.

## Visual check
[sample_trades.png](sample_trades.png): levels and touch-and-reject bars as defined;
SL 4 pips beyond the level, TP 1.5×. The 02-29 short shows the failure mode: price
rejected 1.0850 once, then broke straight through into the stop. Interactive `strategy.visualize` not run (no notebook).

## Interpretation
No edge. A 1m touch-and-reject at a round number is no better than random, and
**00 levels were the worst**. That fits Osler's *other* finding: stop-loss orders
cluster just beyond round numbers, and once they trigger the move accelerates through
the level. On 1m bars a "rejection" is often just the pause before that cascade.
Post hoc, not evidence.

## Decision
**discard**.
**Why:** gross −91.8 (no edge before costs); CI [−1.14, +0.19]; both halves negative;
TP rate below the null; the level the theory favours most (00) performed worst.



Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
