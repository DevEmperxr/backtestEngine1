# 002 — SMA 20/50 crossover, NY-open window, trades left to run

**Date:** 2026-10-05
**File:** research/strategies/002_sma_nywin_letrun.py
**Status:** exploring

## Hypothesis
*(written and committed before any code or backtest — pre-registration)*

EURUSD momentum is strongest in the London/New York overlap: US data releases and the
overlap's order flow push sustained intraday moves. A 5m SMA 20/50 crossover taken
only from 1h before the NY open (07:00 New York) until the London close
(16:00 London) should therefore catch moves that continue long enough to hit a
1.5R target more often than random-walk odds. Identical to 001 except trades are not
force-closed at 16:00: tests whether the time exit helps (cuts drift after the overlap) or hurts (cuts winners short).

**Prior (set before running):** sceptical. Neely & Weller (2003) found no excess
returns from intraday FX technical rules after realistic costs. The default
expectation is "no edge"; only clear evidence should overturn it.

## Parameters (fixed in advance, no tuning)
- signal: SMA(20) vs SMA(50) of mid close on 5m bars; long on cross up, short on cross down
- entries only if the entry time (= signal bar close_time) is in
  [07:00 America/New_York, 16:00 Europe/London), Mon–Fri, DST-aware
- entry at the next 5m bar's open (engine t+1); SL/TP resolved on the 1s path
- `exit_on_opposite_signal = False`, no reversal
- **SL 10 pips / TP 15 pips (fixed)**
- **no time exit**: positions opened in the window run until SL or TP (may be held overnight)

### Why SL 10 / TP 15 (chosen before any backtest)
- Volatility in the window (2024 5m bars, 07:00 NY–16:00 London): median ATR(14)
  3.9 pips (IQR 3.0–5.4); median 2h forward excursion ~10 pips each way.
  SL = ~2.5 × median ATR — inside the 1.5–3 × ATR range traders commonly use
  for day-trade stops (practitioner convention, not an academic result), and
  wide enough to sit clear of 5m noise.
- TP = 1.5 × SL: reachable within the window on a meaningful share of days
  (2h forward excursion p75 ≈ 17 pips).
- Kaminski & Lo (2014): stops only add value if returns have momentum. Under a
  random walk an SL/TP bracket has win rate ≈ SL/(SL+TP) = **40%** and expectancy
  ≈ −costs, whatever SL/TP is chosen. This gives a null benchmark that does not
  depend on the exit choice; every trade here ends at SL or TP (or end of data), so the 40% baseline applies cleanly.

## Pre-registered evaluation plan
- Full adversarial suite (verdict, bootstrap CI, gross vs net, MC drawdown,
  ex-best-month/trades).
- **Stability split:** report H1 (Jan–Jun 2024) and H2 (Jul–Dec 2024) separately.
  A real edge should have the same sign in both halves.
- **Null comparison:** win rate vs the 40% random-walk baseline, expectancy vs
  −spread.
- **Lookahead audit:** every `entry_time` must equal the `close_time` of a bar
  where the SMA crossover actually happened, and that close_time must be inside
  the window.
- **Trial count:** this is trial 2 of 3 pre-registered variants (001–003). Any
  later variant counts as an extra trial and must be reported as such.

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
