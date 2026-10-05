# 002 — SMA 20/50 crossover, NY-open window, trades left to run

**Date:** 2026-10-05
**File:** research/strategies/002_sma_nywin_letrun.py
**Status:** discarded

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
- trades: 266, win rate: 40.2%, net pips: **+15.0** (expectancy +0.06 pips/trade)
- profit factor 1.01, max DD −3.3%, Sharpe 0.08
- exits: 107 TP / 159 SL (no time exit)
- verdict: `profitable` (not withheld). Sample-size gate only; see the CI.

## Adversarial checks
- gross vs net: gross +80.2, spread 65.2, net +15.0 → "profitable after costs"
  (+0.30 pips/trade gross).
- bootstrap CI (expectancy): **[−1.45, +1.56] → straddles zero.** Win-rate CI
  [34.2, 46.2]%.
- MC drawdown: observed −3.30% vs median −2.03%, worst −4.45%, rank 2.6% → not
  fragile (the real ordering was unusually *unlucky*).
- ex-best-month: dropping Nov (+135) → **−120.0**. ex-best-trades: top 1% → −30,
  top 5% → −195.
- **H1/H2 split:** H1 −115.0 (win 36.1%), H2 +130.0 (win 43.5%). **Sign flips.**
- **random-walk null:** win rate 40.23% vs 40.0% null: almost exactly random.
- **001 vs 002 (time-exit effect):** the 68 trades 001 force-closed at 16:00 made
  −18.2 pips there; in 002 the same trades ran to 26 TP / 42 SL = −30.0 pips (median
  3.1 h to resolve). The 16:00 flat saved ~12 pips over 68 trades, which is noise.
- **lookahead audit: passed** (266/266 entries verified).

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
The cleanest null result of the three. With no time exit, every trade is a pure
10/15 bracket, and the win rate (40.2%) matches the random-walk prediction (40%)
almost exactly. The entry carries no directional information. Holding past London
close neither helps nor hurts in any detectable way.

## Decision
**discard**.
**Why:** win rate 40.23% vs 40.0% random-walk null; expectancy CI [−1.45, +1.56]
straddles zero; halves have opposite signs; ex-November −120. The 001-vs-002
comparison shows the 16:00 force-flat makes no meaningful difference (~12 pips
over 68 trades).


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)

## Erratum (2026-10-05, added during run 004; nothing above was changed)
The random-walk null above, SL/(SL+TP) = 40%, ignores the spread: a long enters at
the ask and exits at the bid, so TP needs a mid move of TP + spread and SL only
SL − spread. The spread-adjusted null is ≈ (SL − spread)/(SL + TP) = **39.0%** here,
against an actual 40.2% (z ≈ +0.4 standard errors). **The conclusion is unchanged:**
indistinguishable from a random entry. `run_experiment.py` uses the corrected formula
from 004 on.
