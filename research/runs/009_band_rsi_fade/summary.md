# 009 — Bollinger + RSI stretch fade (practitioner mean reversion)

**Date:** 2026-10-05
**File:** research/strategies/009_band_rsi_fade.py
**Status:** discarded

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
- trades: 277 (from 657 in-window signals), win rate 42.2%, net pips: **−190.1**
  (expectancy −0.69/trade)
- profit factor 0.87, avg win +10.8 / avg loss −9.1, max DD −3.8%, Sharpe −1.13
- exits: 85 TP / 124 SL / 68 force-flat
- verdict: `unprofitable`

## Adversarial checks
- gross vs net: gross **−123.7**, spread 66.4 → "no edge — gross P&L not positive".
- bootstrap CI (expectancy): **[−2.04, +0.65]**.
- MC drawdown: observed −3.84% vs median −2.95%, rank 7% → not fragile (unlucky ordering).
- ex-best-month: drop Dec (+88.9) → −279.0; ex top 5% → −523.6.
- **H1/H2:** H1 −202.2 (win 38.3%), H2 +12.2 (win 46.9%).
- **random-walk null (spread-adjusted):** TP-first 40.7% vs 43.2% (z ≈ −0.7).
- **Raised bar:** no on all three counts.
- **lookahead audit: passed.** 277/277 entries verified; independent Bollinger/Wilder-RSI
  recompute with explicit numpy loops on 1s-rebuilt 5m bars: 0 invalid signal bars;
  0 SL mismatches; 0 force-flat violations.

## Visual check
[sample_trades.png](sample_trades.png): entries at closes outside the band with RSI
extreme; TP at the middle band as of the signal bar. The 01-18 long shows the classic
failure: fading a persistent trend while the band walks down with price. Interactive `strategy.visualize` not run (no notebook).

## Interpretation
No edge, as the prior expected for an indicator rule with no peer-reviewed support.
Behaves like a random entry with a bracket, minus costs.

## Decision
**discard**.
**Why:** gross −123.7; CI [−2.04, +0.65]; H1 −202 / H2 +12; TP rate below the null.



Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
