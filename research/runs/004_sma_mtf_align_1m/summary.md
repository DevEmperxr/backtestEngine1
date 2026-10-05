# 004 — 1m SMA cross aligned with 5m + 15m trend, NY-open window, flat at London close

**Date:** 2026-10-05
**File:** research/strategies/004_sma_mtf_align_1m.py
**Status:** exploring

## Hypothesis
*(written and committed before any code or backtest — pre-registration)*

001–003 showed that a 5m SMA 20/50 cross on its own is no better than a random
entry in this window. Many single-timeframe crosses are whipsaws against the
prevailing move. If intraday momentum exists, it should show up when several
timeframes agree. Entering on a 1m SMA 20/50 cross **only when the 5m and 15m
SMA 20/50 trends already point the same way** should filter out
counter-trend whipsaws, so the 1m entry rides an established move and beats the
random-walk odds.

Changed vs 001: (1) the entry (1m trigger + 5m/15m trend filter), and (2) the
exits, re-sized for 1m. A result therefore can't be attributed to one change
alone (user's choice; a later run can separate them).

**Prior (set before running):** sceptical. Neely & Weller (2003): no excess
returns from intraday FX technical rules after realistic costs. Extra risk here:
4-pip stops make the ~0.2-pip spread ~5% of the risk per trade (vs ~2% in 001), so
costs bite harder.

## Parameters (fixed in advance, no tuning)
- signal frame: 1m bars (resampled from 1s); entry at the next 1m bar's open (engine t+1)
- trigger: SMA(20) crosses SMA(50) of 1m mid close
- filter: on the **last closed** 5m bar and the **last closed** 15m bar (bars built
  from the 1m mid closes), SMA(20) > SMA(50) for longs / < for shorts.
  A higher-timeframe bar is visible to 1m row t only if its close_time ≤ row t's
  close_time (as-of backward join): no peeking at a forming 5m/15m candle.
- window: entry time (= signal bar close_time) in [07:00 America/New_York,
  16:00 Europe/London), Mon–Fri, DST-aware (same as 001)
- `exit_on_opposite_signal = False`, no reversal; force-flat at 16:00 London (same as 001)
- **SL 4 pips / TP 6 pips (fixed)**

### Why SL 4 / TP 6 (chosen before any backtest)
- 1m ATR(14) in the window, 2024: median 1.66 pips (IQR 1.25–2.33); H1 1.54, H2 1.78.
- Same rule as 001 on the new timeframe: SL = 2.5 × median ATR = 4.15 → 4 pips
  (the H1-only median gives 3.85 → also 4); TP = 1.5 × SL = 6.
- Random-walk null: TP-first rate = 4/(4+6) = **40%**, expectancy ≈ −costs.

## Pre-registered evaluation plan
- Full adversarial suite; H1/H2 split; random-walk null (40%).
- **Comparison to 001:** does the trend filter move the TP rate above 40% and the
  expectancy CI off zero, where 001 failed?
- **Lookahead audit:** every entry at the close of a 1m bar with the matching cross,
  inside the window; **independent re-check of the filter**: for every trade,
  rebuild 5m/15m bars from the 1s data with `lib.data.resample` (a separate code
  path), take the last bar with close_time ≤ entry time, and confirm its SMA 20/50
  trend matches the trade direction. 0 force-flat violations.
- **Trial count:** trial 4 in this research line (001–003 were discarded). Any
  tuning of SMA periods, the timeframes, or SL/TP after seeing results is a new trial.

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
