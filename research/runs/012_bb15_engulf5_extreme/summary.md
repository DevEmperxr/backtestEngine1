# 012 — 15m Bollinger stretch + 5m "outside" engulfing confirmation, stop beyond the setup extreme

**Date:** 2026-10-05
**File:** research/strategies/012_bb15_engulf5_extreme.py
**Status:** discarded

## Hypothesis
*(written and committed before any P&L; 012 and 013 registered together)*

User's idea, following 010/011: replace the late 5m SMA 9/21 cross with a **5m
"outside" engulfing candle** as the reversal confirmation. An engulfing candle
marks the turn on the bar it happens, rather than after averages have caught up.
So the entry should come earlier, with more of the move back to the 15m middle
band still left to capture.

**Honest status: data-informed variant** (motivated by 010/011's "late confirmation"
finding), **trial 12 on 2024**. Literature: candlestick signals alone show no value
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
- **SL (012):** setup extreme (lowest 5m mid low / highest high from the start of the
  setup 15m bar through the signal bar) ± 2 pips.

Seen before registering (no P&L): 1,163 signals in 2024; median TP 8.2 pips, median
SL 11.0; TP < SL on 698; TP < 2 pips on 72.

## Pre-registered evaluation plan
- full adversarial suite; H1/H2; spread-adjusted random-walk null.
- independent audit: 15m bands recomputed with numpy on 1s-rebuilt bars (setup within
  120 min before entry), and the engulfing condition re-checked on 1s-rebuilt 5m bars.
- **direct comparison to 010** (same setup logic, different confirmation).
- **raised bar (trial 12):** CI excludes 0 AND both halves positive AND TP rate ≥ 2 SE
  above the spread-adjusted null.

## Headline result
- trades: 415 (1,163 signals; many fired mid-trade), win rate 47.7%, net **−157.8** pips
  (expectancy −0.38/trade)
- profit factor 0.91, avg win +7.9 / avg loss −8.0, max DD −2.9%, Sharpe −0.91
- exits: 138 TP / 185 SL / 92 force-flat
- verdict: `unprofitable`

## Adversarial checks
- gross vs net: gross **−61.2**, spread 96.5 → "no edge — gross P&L not positive".
- bootstrap CI (expectancy): **[−1.29, +0.53]**.
- MC drawdown: −2.94% vs median −2.80%, rank 40% → `fragile` flag (borderline); moot.
- ex-best-month: drop Nov (+66.9) → −224.7; ex top 5% → −605.5.
- **H1/H2:** H1 −193.6 (win 44.0%), H2 +35.8 (win 52.5%).
- **random-walk null (spread-adjusted):** TP-first 42.7% vs **47.6%** null (z ≈ −1.75):
  *worse* than random.
- **vs 010 (same setup, SMA-cross confirm):** the engulfing confirmation did produce
  earlier entries (median TP 8.2 vs 5.8 pips) and 4× the trades, but the extra room was
  not captured: TP-first fell from at-null (010) to below-null.
- **Raised bar:** no on all three counts.
- **lookahead audit: passed.** 415/415 entries; independent recompute on 1s-rebuilt bars:
  0 trades without a 15m setup in the 120-min life, 0 without the outside-engulfing
  condition on the signal bar; 0 SL mismatches; 0 force-flat violations.

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
**Why:** gross −61.2 (no edge before costs); CI [−1.29, +0.53]; H1 −194; TP-first 1.75 SE
*below* the spread-adjusted null; fails the raised bar on every count.


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
