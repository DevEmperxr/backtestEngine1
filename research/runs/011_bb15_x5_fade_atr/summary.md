# 011 — 15m Bollinger stretch + 5m SMA 9/21 cross confirmation, stop 2.5 × 5m ATR

**Date:** 2026-10-05
**File:** research/strategies/011_bb15_x5_fade_atr.py
**Status:** exploring

## Hypothesis
*(written and committed before any code or backtest — pre-registration; 010 and 011 registered together)*

User's idea. A 15m close outside the 2σ Bollinger band marks an overstretched move.
Fading it straight away (009) caught falling knives. Waiting for a **5m SMA 9/21
cross back in the reversion direction** should confirm the short-term turn, so the
trade enters only once the stretch has started to unwind. The target is set "a bit
before" the 15m middle band, to exit ahead of the obvious level where other
participants' take-profits sit (Osler 2003).

**Prior:** sceptical. 009 (a 5m band fade) and 008 had no edge; mean-reversion
evidence for intraday FX outside the fix effect is weak. More rules mean more free
settings, and trials 10–11 on the same year.

## Rules (fixed in advance)
- signal frame: 5m bars (resampled from 1s), mid prices.
- **15m Bollinger** from closed 15m bars only (as-of on close_time, `higher_tf_join`):
  mid = SMA(20) of 15m closes, bands = mid ± 2 × SD(20).
- **setup (long):** a closed 15m bar's close < its lower band. Setup time = that bar's close_time.
  Short: close > upper band. A later qualifying 15m close refreshes the setup.
- setup **valid for 60 min** (5m rows with close_time ≤ setup time + 60m), and
  **cancelled** if any 5m bar since the setup reached the current 15m middle band
  (high ≥ mid for a long setup / low ≤ mid for a short) before the confirming cross.
- **confirmation:** 5m SMA(9) crosses above SMA(21) of 5m mid close (long) / below (short),
  on a 5m bar inside an active setup, with the close still on the far side of the 15m mid.
- entry at the next 5m open; window 07:00 NY → 16:00 London (entry time = signal bar
  close_time), Mon–Fri; force-flat 16:00 London; `exit_on_opposite_signal = False`.
- **TP** = 0.8 × |signal close − 15m middle band| (user: "a bit before the middle band").
- **SL (011):** 2.5 × ATR(14) of 5m mid bars at the signal bar (same rule as 003/009). Identical to 010 otherwise.

## Pre-registered evaluation plan
- full adversarial suite; H1/H2; spread-adjusted random-walk null.
- independent audit: 15m and 5m bars rebuilt from 1s with `lib.data.resample`, bands
  and SMAs recomputed with numpy; for every trade, confirm a qualifying 15m close
  ≤ 60 min before entry and a matching 5m cross on the signal bar.
- **raised bar (trial 11 on 2024):** CI excludes 0 AND both halves positive AND TP rate
  ≥ 2 SE above the spread-adjusted null.

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
