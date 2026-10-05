# 013 — 15m Bollinger stretch + 5m "outside" engulfing confirmation, stop beyond the engulfing candle

**Date:** 2026-10-05
**File:** research/strategies/013_bb15_engulf5_candlestop.py
**Status:** exploring

## Hypothesis
*(written and committed before any P&L; 012 and 013 registered together)*

User's idea, following 010/011: replace the late 5m SMA 9/21 cross with a **5m
"outside" engulfing candle** as the reversal confirmation. An engulfing candle
marks the turn on the bar it happens, rather than after averages have caught up.
So the entry should come earlier, with more of the move back to the 15m middle
band still left to capture.

**Honest status: data-informed variant** (motivated by 010/011's "late confirmation"
finding), **trial 13 on 2024**. Literature: candlestick signals alone show no value
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
- close still on the far side of the 15m mid; window 07:00 NY → 16:00 London, Mon–Fri;
  entry next 5m open; force-flat 16:00 London; `exit_on_opposite_signal = False`.
- **TP** = 0.8 × |signal close − 15m middle band|.
- **SL (013):** beyond the engulfing (signal) bar itself: its 5m mid low − 2 pips (long) / high + 2 pips (short).

Seen before registering (no P&L): 1,163 signals in 2024; median TP 8.2 pips, median
SL 5.8; TP < SL on 366; TP < 2 pips on 72.

## Pre-registered evaluation plan
- full adversarial suite; H1/H2; spread-adjusted random-walk null.
- independent audit: 15m bands recomputed with numpy on 1s-rebuilt bars (setup within
  120 min before entry), and the engulfing condition re-checked on 1s-rebuilt 5m bars.
- **direct comparison to 012** (same entries, different stop).
- **raised bar (trial 13):** CI excludes 0 AND both halves positive AND TP rate ≥ 2 SE
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
