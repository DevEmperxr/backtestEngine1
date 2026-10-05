# 014 — as 012, window extended to 08:00 London → 16:00 New York

**Date:** 2026-10-05
**File:** research/strategies/014_bb15_engulf5_extreme_lonny.py
**Status:** discarded

## Hypothesis
*(written and committed before any P&L; 014 and 015 registered together)*

**Change vs 012: only the trading window**, from 07:00 NY → 16:00 London to
**08:00 London (London open) → 16:00 New York** (NY close; 16:00 not 17:00 to avoid the
rollover spread, as in 006). Force-flat moves to 16:00 NY. User's request after 012/013.
**Data-informed**: the post-London-close period is where 006/007 saw reversals on this
same 2024 data. **Trial 14 on 2024.**

Original 012/013 hypothesis, unchanged:

User's idea, following 010/011: replace the late 5m SMA 9/21 cross with a **5m
"outside" engulfing candle** as the reversal confirmation. An engulfing candle
marks the turn on the bar it happens, rather than after averages have caught up.
So the entry should come earlier, with more of the move back to the 15m middle
band still left to capture.

**Honest status: data-informed variant** (motivated by 010/011's "late confirmation"
finding), **trial 14 on 2024**. Literature: candlestick signals alone show no value
on large US stocks (Marshall, Young & Rose 2006, JBF). FX evidence is mixed and
generally too small to beat costs. Here the candle is only the confirmation of a
15m stretch.

**Prior:** sceptical.

## Rules (fixed in advance; identical to 010 as amended, except the confirmation)
- 5m bars from 1s, mid prices; 15m Bollinger(20, 2) from closed 15m bars only.
- setup: closed 15m close outside the band (long below lower / short above upper);
  valid **120 min**; cancelled if a 5m bar since the setup reached the current 15m
  middle band.
- **confirmation (new):** bullish = 5m mid close > mid open AND mid close > the previous
  5m bar's mid high; bearish = close < open AND close < previous bar's mid low
  (the user's "close beyond prior high/low" definition). Only bars t-1 and t are used.
- close still on the far side of the 15m mid; window **08:00 London → 16:00 New York**, Mon–Fri;
  entry next 5m open; force-flat **16:00 New York**; `exit_on_opposite_signal = False`.
- **TP** = 0.8 × |signal close − 15m middle band|.
- **SL (012):** setup extreme (lowest 5m mid low / highest high from the start of the
  setup 15m bar through the signal bar) ± 2 pips.

Seen before registering (no P&L): 3,569 signals in 2024; median TP 7.4 pips, median SL 10.0.

## Pre-registered evaluation plan
- full adversarial suite; H1/H2; spread-adjusted random-walk null.
- independent audit: 15m bands recomputed with numpy on 1s-rebuilt bars (setup within
  120 min before entry), and the engulfing condition re-checked on 1s-rebuilt 5m bars.
- **direct comparison to 012** (same rules, narrower window): also split trades by
  entry before / after 16:00 London (descriptive).
- **raised bar (trial 14):** CI excludes 0 AND both halves positive AND TP rate ≥ 2 SE
  above the spread-adjusted null.

## Headline result
- trades: **1,057** (3,569 signals), win rate 46.8%, net **−15.9** pips (expectancy −0.02/trade)
- profit factor 1.00, avg win +8.7 / avg loss −7.7, max DD −3.1%, Sharpe −0.05
- exits: 439 TP / 527 SL / 91 force-flat
- verdict: `unprofitable`

## Adversarial checks
- gross vs net: gross **+221.1**, spread 237.0 → "edge existed, costs ate it". Gross
  +0.21 pips/trade vs 0.22 spread.
- bootstrap CI (expectancy): **[−0.60, +0.57]**. With ~1,000 trades this is the tightest
  CI so far: any real edge here is smaller than ~0.6 pips/trade.
- MC drawdown: −3.06% vs median −3.40%, rank 67% → `fragile` flag; moot.
- ex-best-month: drop Dec (+71.7) → −87.5; ex top 1% (11) → −381.3; ex top 5% → −1,281.5.
- **H1/H2:** H1 −133.0 (gross ≤ 0), H2 +117.1. Not stable.
- **Pre-registered split:** entries before 16:00 London 864 trades, −62.1; at/after 16:00
  London 193 trades, **+46.2** (CI [−0.97, +1.55]).
- **random-walk null (spread-adjusted):** TP-first 45.5% vs 46.5% (z ≈ −0.65).
- **vs 012 (narrow window):** −157.8 → −15.9. The wider window dilutes the loss, but the TP
  rate is still at the null.
- **Raised bar:** no on all three counts.
- **lookahead audit: passed.** 1,057/1,057 entries; independent 15m-setup and engulfing
  re-checks: 0 failures; 0 SL mismatches; 0 force-flat violations (vs 16:00 NY).

## Visual check
[sample_trades.png](sample_trades.png): entries now start from the London open
(e.g. 01-23 08:05 London); setup → outside-engulfing → entry logic, the TP at 80% of the way
to the 15m mid and the SL are as registered; force-flat at 16:00 NY. Nothing wrong
mechanically. Interactive `strategy.visualize` not run.

## Interpretation
No edge. With 1,000+ trades this is now a fairly *informative* null, not just a noisy
one. Win rates sit on the random-walk baseline, gross P&L is about +0.1–0.2 pips/trade
(within noise of zero) and smaller than the spread, and the CI rules out anything
larger than ~0.6 pips/trade.

The pre-registered split is the one consistent detail. In both runs the trades entered
**after 16:00 London** were positive (+46 and +94), while those entered before were
negative. It's the same direction as 006 and 007 (reversion after the London fix). But
each CI includes zero, and it's the *third* look at the post-fix period on 2024 data,
so it adds weight to carrying 007 forward to new data, not evidence on its own.

## Decision
**discard**.
**Why:** net −15.9 over 1,057 trades; CI [−0.60, +0.57]; gross +0.21/trade < spread; TP rate at
the null; H1 negative. Fails the raised bar on every count.


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
