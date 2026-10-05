# 006 — ORB as 005, but the window and force-flat move to 16:00 New York

**Date:** 2026-10-05
**File:** research/strategies/006_orb_ny_prenews_nyclose.py
**Status:** discarded

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
- trades: 258, win rate 43.4%, net pips: **−510.6** (expectancy −1.98 pips/trade)
- profit factor 0.78, max DD −5.95%, Sharpe −1.76
- exits: 71 TP / 115 SL / 72 force-flat at 16:00 NY
- verdict: `unprofitable` (not withheld)

## Adversarial checks
- gross vs net: gross **−446.9**, spread 63.7 → "no edge — gross P&L not positive".
- bootstrap CI (expectancy): **[−4.18, +0.16]**, almost entirely negative.
- MC drawdown: observed −5.95% vs median −6.11%, rank 59% → `fragile` flag; moot.
- ex-best-month: dropping Feb (+76.2) → −586.8; ex top 5% trades → −897.1.
- **H1/H2:** H1 −217.3 (win 45.7%), H2 −293.3 (win 41.2%). Negative in both.
- **News split:** NFP/CPI 24 trades −44.3; other days 234 trades −466.2.
- **random-walk null (spread-adjusted):** TP-first 38.2% vs 44.4% null (z ≈ −1.7).
- **Raised bar (pre-registered):** CI excludes 0? no. Both halves positive? no. TP rate
  ≥ 2 SE above null? no (it is 1.7 SE *below*). → not a candidate.
- **Direct comparison to 005 (pre-registered):** all 255 of 005's entries recur in 006;
  the 137 trades 005 closed at SL/TP are identical. The **118 trades still open at
  16:00 London were +153.5 pips at that moment (005); held to 16:00 NY they ended
  −215.2** (69 time-exit, 34 SL, 15 TP): −369 pips from the extra hours. 3 extra
  late-breakout trades made the rest of the difference (+23).
- **lookahead audit: passed.** 258/258 entries verified; independent ORB re-check clean;
  0 force-flat violations against 16:00 NY.

## Visual check
Static render of 4 random trades (seed 7): [sample_trades.png](sample_trades.png). Force-flat
exits land at 16:00 NY; range, entries and SL/TP as in 005. Example of the main
effect: 2024-01-22 short, in profit through the London session, drifts back up
after the London close and stops out at 12:33 NY.

## Interpretation
More time made it worse, not better. The breakout trades still open at the London
close were, on aggregate, slightly in profit. In the US afternoon they **reversed**:
of 118, 34 hit SL and only 15 hit TP. So whatever directional push the morning
breakout has (005 showed it is not distinguishable from random), it does not
persist past the London close. If anything, it gives back.

Post hoc, **not** evidence (a new trial if acted on): this looks like a
"London-close reversal". It may link to FX fixing flows: the WM/Reuters 4pm London
fix is a known liquidity event, and the literature reports return patterns around
fixes (e.g. Krohn, Mueller & Whelan on FX fixings; not re-checked in this session).
It would need its own pre-registered hypothesis and ideally fresh data.

## Decision
**discard**.
**Why:** −510.6 pips, gross −446.9; expectancy CI [−4.18, +0.16]; both halves negative;
TP rate 1.7 SE below the null; fails every part of the pre-registered raised bar. The
16:00 London force-flat in 005 was *protecting* the strategy (+369 pips vs holding to
the NY close), not cutting winners short.


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
