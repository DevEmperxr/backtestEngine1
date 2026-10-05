# 005 — Opening-range breakout: 07:00–08:30 NY range, break after the 08:30 data

**Date:** 2026-10-05
**File:** research/strategies/005_orb_ny_prenews.py
**Status:** discarded

## Hypothesis
*(written and committed before any code or backtest — pre-registration)*

In equities the ORB edge is concentrated where a catalyst creates one-sided order
flow ("Stocks in Play", Zarattini, Barbon & Aziz 2024), and intraday momentum is
strongest on macro-news days (Gao, Han, Li & Zhou 2018, JFE). The FX analogue in
this window is the 08:30 New York US data release. EURUSD tends to range while
traders wait for the 08:30 number. A break of that pre-news range (07:00–08:30 NY)
afterwards should reflect new information plus the order flow of the US session,
and keep going far enough to reach a 1.5×-range target more often than a
random entry would.

**Prior (set before running):** sceptical. 001–004 found nothing in this window.
I found no peer-reviewed support for FX session-range breakouts, and the retail
London-breakout backtests I found are mostly negative. Holmberg, Lönnbark &
Lundström (2013) and Crabel (1990) support ORB in other markets.

## Rules (fixed in advance, no tuning)
- signal frame: 1m bars resampled from 1s; all levels on mid = (bid + ask)/2
- **opening range** per New York date: high = max of 1m mid highs, low = min of 1m mid
  lows over bars with timestamp ≥ 07:00 NY and close_time ≤ 08:30 NY (90 bars).
  Day skipped if fewer than 90 range bars exist.
- **breakout**: a 1m bar with close_time in (08:30 NY, 16:00 London) whose mid close is
  > range high (long) or < range low (short). **Only the day's first breakout bar** is
  a signal (one trade per day max). Entry at the next 1m open (engine t+1).
- **SL** at the opposite side of the range: sl_pips = |signal mid close − opposite
  boundary| / pip (per trade, set at the signal bar).
- **TP** = 1.5 × range height (per trade).
- force-flat at 16:00 London (`exit_signal`); `exit_on_opposite_signal = False`.
- no other filters (no NR7, no trend, no news filter).

## Pre-registered evaluation plan
- Full adversarial suite; H1/H2 split; spread-adjusted random-walk null
  (mean of (SL − spread)/(SL + TP) over SL/TP-resolved trades).
- **News split (reported, not a filter):** trades on BLS Employment Situation or CPI
  release days (24 dates, all 08:30 ET, from bls.gov/schedule/2024) vs all other
  days. With ~24 news-day trades at most, this is descriptive only.
- Also recorded: range-height distribution, share of days with no breakout, exits by type.
- **Lookahead audit:** entry at the close of the signal bar; signal bar closes after
  08:30 NY and before 16:00 London; **independent re-check:** rebuild 1m bars from the
  1s data, recompute the 07:00–08:30 range with separate code, and confirm that the
  signal bar is the first close beyond it that day, that the side matches the direction,
  and that there is at most one trade per day; 0 force-flat violations.
- **Trial count:** trial 5 overall in this window (001–004 discarded), trial 1 of the ORB
  line. Changing range times, target multiple, or adding filters after seeing results
  = new trials.

## Headline result
- trades: 255 (a breakout on 255 of the ~260 trading days), win rate 48.2%, net pips:
  **−165.4** (expectancy −0.65 pips/trade)
- profit factor 0.91, avg win +13.1 / avg loss −13.4, max DD −3.0%, Sharpe −0.66
- exits: 56 TP (+1,036.6) / 81 SL (−1,355.5) / **118 force-flat at 16:00** (+153.5)
- per-trade SL p10/50/90 = 10.7 / 16.4 / 34.1 pips; TP 13.6 / 21.0 / 34.9; range height
  9.1 / 14.0 / 23.3. **40 trades had SL > TP**: the first close overshot the range
  (e.g. NFP 2024-01-05: closed 32 pips beyond it → SL 46 / TP 21)
- timing: half the breakouts come within 5 minutes of 08:30 NY (123 of 255; median 6 min)
- verdict: `unprofitable` (not withheld)

## Adversarial checks
- gross vs net: gross **−104.3**, spread 61.1 → "no edge — gross P&L not positive".
- bootstrap CI (expectancy): **[−2.55, +1.25] pips/trade → straddles zero.**
- MC drawdown: observed −2.98% vs median −3.35%, rank 70% → `fragile` flag (milder than
  most shuffles). Moot without an edge.
- ex-best-month: dropping Sep (+77.4) → −242.7; ex top 5% trades → −508.8.
- **H1/H2 split:** H1 +15.7 (125 trades, win 50.4%), H2 −181.1 (130, win 46.2%). Not stable.
- **News split (descriptive, n tiny):** NFP/CPI days 24 trades, −4.0 pips, win 50%, CI
  [−8.4, +7.6]; other days 231 trades, −161.4. No visible news-day edge, and 24
  trades could not show one anyway.
- **random-walk null (spread-adjusted):** TP-first 40.9% vs **45.5%** null (z ≈ −1.1):
  at or slightly below random.
- direction (post hoc): shorts +93.7 (127), longs −259.1 (128). Probably EURUSD's 2024
  H2 downtrend (1.12 → 1.04). Not evidence of anything structural.
- **lookahead audit: passed.** 255/255 entries at the signal-bar close, inside the window;
  **independent ORB re-check** (range recomputed from 1s→1m bars with separate code):
  0 missing ranges, 0 signals not beyond the range, 0 signals at/before 08:30, 0 not
  the day's first breakout, 0 days with >1 trade; 0 force-flat violations; 0 SL
  mismatches vs the signal bar.

## Visual check
Static render of 4 random trades (seed 7): [sample_trades.png](sample_trades.png). The
07:00–08:30 NY range is shaded; the range lines appear only after 08:30 (hidden before,
as built); entry one bar after the first close beyond the range; SL at the opposite
side; the 16:00 London force-flat lands at 11:00 NY in summer. Nothing wrong
mechanically. Interactive `strategy.visualize` not run (no notebook).

## Interpretation
No edge. Breaking the pre-news range is no better than a random entry with the same
bracket. Gross P&L is negative, the TP rate sits at or below the spread-adjusted null,
the halves disagree, and NFP/CPI days show nothing different (too few to say more).

Structural notes (post hoc, each would be a new trial if acted on):
- 46% of trades ended at the 16:00 force-flat. A 1.5× range target (median 21 pips)
  is often too far for the ~2.5–7.5 h left in the window.
- Half the "breakouts" are the 08:30 news bar itself. A close-based entry after a
  news spike often buys the extreme, and the stop measured from that close then
  becomes very wide (40 trades with SL > TP).

Equity-market ORB evidence (Zarattini et al.) relies on picking *which* instruments
are "in play" each day. A single FX pair traded every day has no such selection, and
that may be the missing ingredient.

## Decision
**discard**.
**Why:** gross −104.3 pips (no edge before costs); expectancy CI [−2.55, +1.25] straddles
zero; H1 +15.7 vs H2 −181.1; TP rate 40.9% vs 45.5% spread-adjusted null; no
news-day effect visible.


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
