# 007 — Fade the run-up into the 16:00 London fix, hold to 16:00 New York

**Date:** 2026-10-05
**File:** research/strategies/007_fix_fade_london.py
**Status:** discarded

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
- trades: 260 (every weekday), win rate 51.9%, net pips: **+39.4** (expectancy +0.15/trade)
- profit factor 1.02, avg win +12.9 / avg loss −13.7, max DD −2.0%, Sharpe 0.14
- exits: 252 time-exit at 16:00 NY, 6 SL, 2 TP (the 50-pip disaster bracket barely matters)
- verdict: `profitable` (sample-size gate only)

## Adversarial checks
- gross vs net: gross +90.1, spread 50.7 → "profitable after costs" (+0.35 gross/trade).
- bootstrap CI (expectancy): **[−1.96, +2.29] → straddles zero.**
- MC drawdown: observed −1.99% vs median −2.75%, rank 90% → `fragile` (real ordering
  unusually kind).
- ex-best-month: drop Jan (+65.2) → −25.8; ex top 1% (3 trades) → −105.4; ex top 5% → −460.1.
- **H1/H2:** H1 −11.4 (win 49.6%), H2 +50.8 (win 54.2%). Not both positive.
- **Pre-registered |r| split (descriptive):** big pre-fix move (|r| > median): 130 trades
  **+217.7**, win 59.2%, CI [−1.51, +4.85]; small pre-fix move: 130 trades **−178.3**, win
  44.6%, CI [−4.20, +1.50].
- **Raised bar:** CI excludes 0? no. Both halves positive? no. → not a candidate.
- **lookahead audit: passed.** 260/260 entries at the fix bar's close inside the window;
  independent recompute of the 15:00→16:00 move from 1s-rebuilt bars: 0 entries off
  16:00 London, 0 direction mismatches, 0 missing bars; 0 force-flat violations.

## Visual check
[sample_trades.png](sample_trades.png): entries at 16:00 London, opposite to the
15:00→16:00 move in all four samples (checked by eye); exits at 21:00 London = 16:00 NY;
the 50-pip bracket sits far outside the path. Interactive `strategy.visualize` not run (no notebook).

## Interpretation
As expected from the power calculation, one year cannot resolve this. The total is
slightly positive, but the CI is ±2 pips/trade wide and H1 is negative.

The pre-registered split is the one thing pointing the way the paper predicts. Krohn,
Mueller & Whelan's conditional result says a *larger* pre-fix move should reverse
*more*: big-move days made +217.7, small-move days −178.3. But both CIs include zero,
it is one split of one year, and 2024 is contaminated by the 006 observation. It is a
hypothesis worth carrying forward, not a finding.

## Decision
**discard on 2024 (not a candidate); re-test on other years.**
**Why:** expectancy CI [−1.96, +2.29] straddles zero; H1 negative; fails the raised bar.
Carry forward as a pre-specified out-of-sample test: *fade the 15:00→16:00 London move
only when |move| is above its trailing median*. Its threshold must come from past data
only (e.g. a trailing 60-day median), never from 2024's full-year median. It must be
tested on years other than 2024.



Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
