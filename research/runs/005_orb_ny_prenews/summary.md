# 005 — Opening-range breakout: 07:00–08:30 NY range, break after the 08:30 data

**Date:** 2026-10-05
**File:** research/strategies/005_orb_ny_prenews.py
**Status:** exploring

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
_(filled after the run)_

## Adversarial checks
_(filled after the run)_

## Visual check
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
