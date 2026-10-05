# 003 — SMA 20/50 crossover, NY-open window, ATR-scaled SL/TP, flat at London close

**Date:** 2026-10-05
**File:** research/strategies/003_sma_nywin_atr.py
**Status:** discarded

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
- trades: 273, win rate: 37.7%, net pips: **−166.6** (expectancy −0.61 pips/trade)
- profit factor 0.88, avg win +12.0 / avg loss −8.3, max DD −3.2%, Sharpe −0.96
- exits: 69 TP / 122 SL / 82 force-flat
- per-trade SL (2.5 × ATR14): min 3.7, p10 5.9, median 9.3, p90 18.7, max 31.8 pips
- verdict: `unprofitable` (not withheld)

## Adversarial checks
- gross vs net: gross **−102.7**, spread 63.9 → "no edge — gross P&L not positive".
- bootstrap CI (expectancy): **[−1.92, +0.75] → straddles zero.**
- MC drawdown: observed −3.17% vs median −2.77%, rank 24.7% → not fragile.
- ex-best-month: dropping Oct (+59.4) → −226.0. ex-best-trades: top 5% → −481.2.
- **H1/H2 split:** H1 −133.5 (win 36.6%), H2 −33.2 (win 38.7%). Negative in both.
- **random-walk null:** TP-first rate 36.1% vs 40.0% null (below random, within noise).
- **lookahead audit: passed.** 273/273 entries verified; 0 force-flat violations;
  0 trades whose SL differs from 2.5 × ATR at the signal bar.

## Visual check
Static render of 4 randomly sampled trades (seed 7) at the strategy's own 5m
timeframe: [sample_trades.png](sample_trades.png). Checked: each entry is one bar
after a real SMA20/SMA50 cross, inside the shaded window (12:00–16:00 London);
SL/TP lines at the logged distances; force-flat exits land at exactly
16:00:00 London. Nothing suspicious. The interactive `strategy.visualize(engine,
show_trades=True)` was **not** run in this session (no notebook); a human pass
in the notebook is still worth doing.

Observation (post hoc, **not** pre-registered): entries in the last 30 min of
the window (15:30–15:55 London) are near-certain to be time-exited before SL/TP
can resolve: 23 trades, −45.7 pips in 001 (−43.9 in 003). Acting on this would
be a data-snooped change and must be logged as a new trial.

## Interpretation
Volatility-scaled exits did not help. Gross P&L is negative and the TP rate is a
little *below* the random-walk null. The CI still straddles zero, so 003 is not
demonstrably worse than 001 either. Its distance from 001 (−167 vs +27) is within
noise for ~270 trades. This is what Kaminski & Lo predict when the entry has no
momentum information: reshaping the exits only reshuffles the noise.

## Decision
**discard**.
**Why:** gross P&L −102.7 (no edge before costs); expectancy CI [−1.92, +0.75]
straddles zero; both halves negative; TP rate 36.1% vs 40% null. Scaling the exits
to volatility cannot rescue an entry that carries no signal.


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)

## Erratum (2026-10-05, added during run 004; nothing above was changed)
The random-walk null above, SL/(SL+TP) = 40%, ignores the spread: a long enters at
the ask and exits at the bid, so TP needs a mid move of TP + spread and SL only
SL − spread. The spread-adjusted null is ≈ (SL − spread)/(SL + TP) = **38.7%** here,
against an actual 36.1% (z ≈ −0.7 standard errors). **The conclusion is unchanged:**
indistinguishable from a random entry. `run_experiment.py` uses the corrected formula
from 004 on.
