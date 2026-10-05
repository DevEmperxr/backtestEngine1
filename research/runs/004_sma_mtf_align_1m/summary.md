# 004 — 1m SMA cross aligned with 5m + 15m trend, NY-open window, flat at London close

**Date:** 2026-10-05
**File:** research/strategies/004_sma_mtf_align_1m.py
**Status:** discarded

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
- trades: 393, win rate: 35.4%, net pips: **−180.7** (expectancy −0.46 pips/trade)
- profit factor 0.82 (avg win +5.8 / avg loss −3.9), max DD −2.0%, Sharpe −2.07
- exits: 131 TP / 244 SL / 18 force-flat at 16:00
- 418 in-window aligned signals; 393 taken (the rest fired while a trade was open)
- verdict: `unprofitable` (not withheld)

## Adversarial checks
- gross vs net: gross **−87.8**, spread 93.0 (avg 0.24 pips/trade, ~6% of the 4-pip risk)
  → "no edge — gross P&L not positive".
- bootstrap CI (expectancy): **[−0.91, +0.02] pips/trade**, almost entirely negative;
  just touches zero.
- MC drawdown: observed −1.97% vs median −2.14%, rank 79% → flagged `fragile` (the real
  ordering was milder than most shuffles). Moot: there's no edge to size.
- ex-best-month: dropping Feb (+23.2) → −203.9; ex top 5% trades → −300.7.
- **H1/H2 split:** H1 −76.1 (win 36.2%), H2 −104.6 (win 34.5%). Negative in both halves,
  so the loss is consistent, not a one-period accident.
- **random-walk null (spread-adjusted):** TP-first rate 34.9% vs **37.6%** null
  (z ≈ −1.1). Slightly worse than random, not significantly.
- **lookahead audit: passed.** 393/393 entries at the close of a matching 1m cross
  inside the window; 0 force-flat violations; **independent re-check vs 5m/15m bars
  rebuilt from the 1s data with `lib.data.resample`: 0 trend mismatches on either
  timeframe.**

## Visual check
Static render of 4 random trades (seed 7) on 1m bars: [sample_trades.png](sample_trades.png),
with the 5m/15m trend values at entry in each title. Entries sit one bar after a 1m
SMA cross; trend signs match the direction; SL/TP at 4/6 pips. Nothing wrong
mechanically. Interactive `strategy.visualize` not run (no notebook).

Observations (post hoc, **not** evidence, any action on them = a new trial):
the 1m cross often fires *after* the short-term move is done, so entries are late;
and "aligned" sometimes means a trend of a fraction of a pip (e.g. 5m +0.15p), so
the filter doesn't demand a strong trend.

## Interpretation
The trend filter did not create an edge. Gross P&L is negative in both halves, and
the TP rate is a little below the spread-adjusted random baseline. If anything,
trend-aligned 1m crosses are slightly *worse* than random, which fits the
"late entry" observation: by the time a 1m SMA20/50 cross confirms a move that
the 5m and 15m already show, much of the move is spent.

**Flipping the signal would not help:** reversed gross would be ≈ +0.22 pips/trade,
against ≈ 0.24 pips/trade of spread, so net ≈ 0. It would also be a data-snooped
trial.

Across 001–004 (4 trials), every SMA-crossover variant in this window is at or
below random-entry quality. That is consistent with the prior and with the
intraday-FX literature.

## Decision
**discard**.
**Why:** gross −87.8 pips (no edge before costs); expectancy CI [−0.91, +0.02];
negative in both halves; TP rate 34.9% vs 37.6% spread-adjusted null. The
multi-timeframe filter did not lift the 1m cross above random. Recommend closing
the SMA-crossover line in this window rather than tuning periods, timeframes or
exits (each would be another trial on the same year of data).


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
