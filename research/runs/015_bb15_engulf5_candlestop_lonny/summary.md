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
_(filled after the run)_

## Adversarial checks
_(filled after the run)_

## Visual check
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
