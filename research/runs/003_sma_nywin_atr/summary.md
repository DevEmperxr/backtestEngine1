# 003 — SMA 20/50 crossover, NY-open window, ATR-scaled SL/TP, flat at London close

**Date:** 2026-10-05
**File:** research/strategies/003_sma_nywin_atr.py
**Status:** exploring

## Hypothesis
*(written and committed before any code or backtest — pre-registration)*

Same momentum idea as 001 (5m SMA 20/50 crossover, 07:00 New York → 16:00 London,
flat at 16:00). The only change: SL/TP scale with current volatility instead of
being fixed. A fixed 10-pip stop is too tight on volatile days (noise stop-outs)
and too loose on quiet days (a target that never gets reached). Scaling both to the
5m ATR at the signal bar should keep the bracket at the same *statistical*
distance every day. This is the volatility-scaled barrier approach of López de
Prado's triple-barrier method. If 003 beats 001, volatility-scaled exits help; if
both are null, the problem is the entry signal, not the exits.

**Prior (set before running):** sceptical, same as 001. Changing the exits
cannot create an edge where the entry has none (Kaminski & Lo 2014).

## Parameters (fixed in advance, no tuning)
- signal, window, entry timing, force-flat at 16:00 London: identical to 001
- ATR(14) on 5m mid-price true range, computed from bars ≤ the signal bar only
- **SL = 2.5 × ATR(14) at the signal bar, TP = 1.5 × SL** (per trade, via the
  engine's per-trade `sl_pips`/`tp_pips` columns)
- The 2.5 multiple is the same calibration as 001 (2.5 × the window's median ATR ≈ 10
  pips). On an average day 001 and 003 risk the same; they differ only in how
  the bracket adapts.

## Pre-registered evaluation plan
Same as 001: full adversarial suite, H1/H2 stability split, null comparison
(random-walk win rate = 1/(1+1.5) = 40%), lookahead audit. In addition: check that the
per-trade `sl_pips` matches 2.5 × ATR(14) computed on bars up to the signal bar.
**Trial count:** trial 3 of 3 pre-registered variants.

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
