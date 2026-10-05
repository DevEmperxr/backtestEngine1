# 013 — 15m Bollinger stretch + 5m "outside" engulfing confirmation, stop beyond the engulfing candle

**Date:** 2026-10-05
**File:** research/strategies/013_bb15_engulf5_candlestop.py
**Status:** discarded

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
- trades: 476, win rate 41.8%, net **−149.3** pips (expectancy −0.31/trade)
- profit factor 0.91, avg win +7.7 / avg loss −6.1, max DD −2.7%, Sharpe −0.91
- exits: 139 TP / 257 SL / 80 force-flat
- verdict: `unprofitable`

## Adversarial checks
- gross vs net: gross **−36.7**, spread 112.6 → "no edge — gross P&L not positive".
- bootstrap CI (expectancy): **[−1.03, +0.44]**.
- MC drawdown: −2.71% vs median −2.61%, rank 43% → `fragile` flag (borderline); moot.
- ex-best-month: drop May (+67.2) → −216.5; ex top 5% → −626.1.
- **H1/H2:** H1 −148.0 (win 39.1%), H2 −1.2 (win 45.2%).
- **random-walk null (spread-adjusted):** TP-first 35.1% vs **39.0%** null (z ≈ −1.6).
- **vs 012 (stop choice):** tighter candle stop → more trades (476 vs 415, quicker exits
  free the engine), similar total (−149 vs −158). Neither stop rescues the entry.
- **Raised bar:** no on all three counts.
- **lookahead audit: passed** (same checks as 012, all 0).

## Visual check
[sample_trades.png](sample_trades.png): setup line (15m close outside the band) precedes
each entry within 2 h; entry right after a 5m bar that closes beyond the previous bar's
high/low; TP 80% of the way to the 15m mid; SL as registered. Failure modes visible: fading
a persistent trend (01-23 long into steadily falling bands) and late-window entries that
the 16:00 flat cuts off (09-05, entered 15:50). Interactive `strategy.visualize` not run.

## Interpretation
No edge, and a little worse than random. Earlier confirmation did what it was meant
to do mechanically: entries came sooner, with more distance to the middle band. But the
reversals didn't follow through. After a 15m close outside the band and a strong 5m
reversal candle, price reached the 80% target *less* often than a random entry with the
same bracket would.

Across 008, 009, 010–013, every intraday mean-reversion rule *inside* the 07:00 NY →
16:00 London window is at or below random. Post hoc reading: this window is the most
liquid, news-driven part of the day, where stretched moves are more often information
than overreaction. The only reversal with a published mechanism (007, the London fix)
sits *after* the window.

## Decision
**discard**.
**Why:** gross −36.7; CI [−1.03, +0.44]; both halves ≤ 0; TP-first 1.6 SE below the null.


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
