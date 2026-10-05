# 009 — Bollinger + RSI stretch fade (practitioner mean reversion)

**Date:** 2026-10-05
**File:** research/strategies/009_band_rsi_fade.py
**Status:** exploring

## Hypothesis
*(written and committed before any code or backtest — pre-registration; 007–009 registered together)*

Practitioner claim: when EURUSD closes outside its 2σ Bollinger band with RSI at an
extreme, the move is overstretched and reverts toward the mean. Liquidity-provision
theory (Nagel 2012) gives a reason reversal could pay. No peer-reviewed intraday-FX
support was found, so this is the weakest-grounded of the three.

**Prior:** strongly sceptical.

## Rules (fixed in advance; textbook defaults, not tuned)
- 5m bars, mid close. Bollinger: SMA(20) ± 2 × rolling SD(20). RSI(14), Wilder smoothing.
- long: close < lower band AND RSI < 30. short: close > upper band AND RSI > 70.
- entry window / force-flat: [07:00 NY, 16:00 London), flat at 16:00 London (as 001).
- entry at the next 5m open; `exit_on_opposite_signal = False`.
- **TP** = |signal close − SMA(20)| (back to the middle band), per trade.
- **SL** = 2.5 × ATR(14) at the signal bar (same rule as 003), per trade.

## Pre-registered evaluation plan
- full adversarial suite; H1/H2; spread-adjusted null.
- independent audit: recompute Bollinger/RSI with separate numpy code from bars rebuilt
  from 1s; confirm each signal bar meets both conditions on the traded side.
- **raised bar (trial 9 on 2024):** CI excludes 0 AND both halves positive AND TP rate
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

