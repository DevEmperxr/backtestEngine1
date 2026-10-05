# 015 — as 013, window extended to 08:00 London → 16:00 New York

**Date:** 2026-10-05
**File:** research/strategies/015_bb15_engulf5_candlestop_lonny.py
**Status:** discarded

## Hypothesis
*(written and committed before any P&L; 014 and 015 registered together)*

**Change vs 013: only the trading window**, from 07:00 NY → 16:00 London to
**08:00 London (London open) → 16:00 New York** (NY close; 16:00 not 17:00 to avoid the
rollover spread, as in 006). Force-flat moves to 16:00 NY. User's request after 012/013.
**Data-informed**: the post-London-close period is where 006/007 saw reversals on this
same 2024 data. **Trial 15 on 2024.**

Original 012/013 hypothesis, unchanged:

User's idea, following 010/011: replace the late 5m SMA 9/21 cross with a **5m
"outside" engulfing candle** as the reversal confirmation. An engulfing candle
marks the turn on the bar it happens, rather than after averages have caught up.
So the entry should come earlier, with more of the move back to the 15m middle
band still left to capture.

**Honest status: data-informed variant** (motivated by 010/011's "late confirmation"
finding), **trial 15 on 2024**. Literature: candlestick signals alone show no value
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
- **SL (015):** beyond the engulfing (signal) bar itself: its 5m mid low − 2 pips (long) / high + 2 pips (short).

Seen before registering (no P&L): 3,569 signals in 2024; median TP 7.4 pips, median SL 5.1.

## Pre-registered evaluation plan
- full adversarial suite; H1/H2; spread-adjusted random-walk null.
- independent audit: 15m bands recomputed with numpy on 1s-rebuilt bars (setup within
  120 min before entry), and the engulfing condition re-checked on 1s-rebuilt 5m bars.
- **direct comparison to 013** (same rules, narrower window): also split trades by
  entry before / after 16:00 London (descriptive).
- **raised bar (trial 15):** CI excludes 0 AND both halves positive AND TP rate ≥ 2 SE
  above the spread-adjusted null.

## Headline result
- trades: **1,229**, win rate 39.7%, net **−153.2** pips (expectancy −0.12/trade)
- profit factor 0.96, avg win +8.5 / avg loss −5.8, max DD −3.2%, Sharpe −0.55
- exits: 436 TP / 722 SL / 71 force-flat
- verdict: `unprofitable`

## Adversarial checks
- gross vs net: gross **+123.6**, spread 276.8 → "edge existed, costs ate it" (+0.10/trade gross).
- bootstrap CI (expectancy): **[−0.58, +0.35]**.
- MC drawdown: −3.22% vs median −3.80%, rank 76% → `fragile` flag; moot.
- ex-best-month: drop Sep (+71.5) → −224.6; ex top 5% → −1,502.6.
- **H1/H2:** H1 −143.5, H2 −9.7. Negative in both.
- **Pre-registered split:** before 16:00 London 993 trades, −247.5 (gross ≤ 0); at/after
  16:00 London 236 trades, **+94.3** (CI [−0.55, +1.37]).
- **random-walk null (spread-adjusted):** TP-first 37.7% vs 38.7% (z ≈ −0.75).
- **vs 013:** −149.3 → −153.2. No change.
- **Raised bar:** no on all three counts.
- **lookahead audit: passed** (same checks as 014, all 0).

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
**Why:** net −153.2; CI [−0.58, +0.35]; both halves negative; TP rate at the null.


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
