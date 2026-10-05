# 001 — SMA 20/50 crossover, NY-open window, flat at London close

**Date:** 2026-10-05
**File:** research/strategies/001_sma_nywin_flat1600.py
**Status:** discarded

## Hypothesis
*(written and committed before any code or backtest — pre-registration)*

EURUSD momentum is strongest in the London/New York overlap: US data releases and the
overlap's order flow push sustained intraday moves. A 5m SMA 20/50 crossover taken
only from 1h before the NY open (07:00 New York) until the London close
(16:00 London) should therefore catch moves that continue long enough to hit a
1.5R target more often than random-walk odds. Closing everything at 16:00 keeps the
bet confined to the window where the momentum is supposed to exist.

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
- **force-flat at 16:00 London** (`exit_signal` on the bar closing at 16:00 → exit at 16:00 bar open)

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
  depend on the exit choice (with the 16:00 time exit some trades close between
  the levels, so compare expectancy, not only win rate).

## Pre-registered evaluation plan
- Full adversarial suite (verdict, bootstrap CI, gross vs net, MC drawdown,
  ex-best-month/trades).
- **Stability split:** report H1 (Jan–Jun 2024) and H2 (Jul–Dec 2024) separately.
  A real edge should have the same sign in both halves.
- **Null comparison:** win rate vs the 40% random-walk baseline, expectancy vs
  −spread.
- **Lookahead audit:** every `entry_time` must equal the `close_time` of a bar
  where the SMA crossover actually happened, and that close_time must be inside
  the window; no trade may still be open after 16:00 London.
- **Trial count:** this is trial 1 of 3 pre-registered variants (001–003). Any
  later variant counts as an extra trial and must be reported as such.

## Headline result
- trades: 266, win rate: 40.6%, net pips: **+26.8** (expectancy +0.10 pips/trade)
- profit factor 1.02, avg win +12.5 / avg loss −8.4, max DD −2.1%, Sharpe 0.17
- exits: 81 TP / 117 SL / 68 force-flat at 16:00 (force-flat trades: −18.2 pips total)
- verdict: `profitable` (not withheld; 266 ≥ 100). **Note:** the framework's verdict
  is gated on sample size only, not significance; see the CI below.

## Adversarial checks
- gross vs net: gross +86.2, spread 59.4 (avg 0.22 pips/trade), net +26.8 →
  "profitable after costs", but +0.32 pips/trade gross is tiny against an 11-pip
  per-trade standard deviation.
- bootstrap CI (expectancy): **[−1.20, +1.42] pips/trade → straddles zero, no
  demonstrable edge.** Win-rate CI [34.6, 46.2]% contains the 40% null.
- MC drawdown: observed −2.08% vs shuffled median −1.75%, worst −4.14%,
  percentile rank 25.7% → flagged `fragile` (just over the 25% threshold). Borderline,
  and irrelevant while there is no edge.
- ex-best-month: dropping Nov (+73.5) → **−46.7**. ex-best-trades: top 1% (3) → −18.2,
  top 5% (14) → −183.2. The whole result rests on one month and a handful of trades.
- **H1/H2 split:** H1 −63.2 pips (119 trades, win 37.8%, "no edge, gross ≤ 0");
  H2 +90.0 (147 trades, win 42.9%). **Sign flips between halves.**
- **random-walk null:** TP-first rate on SL/TP-resolved trades 40.9% vs 40.0% null.
  Indistinguishable from an edge-free entry.
- **lookahead audit: passed.** 266/266 entries sit at the close of a matching in-window
  crossover bar; 0 force-flat violations.

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
No evidence of an edge. Every test agrees: the expectancy CI straddles zero, the
TP rate equals the random-walk 40%, the sign flips between halves, and the small
positive total disappears without November or without the best 3 trades. This is
the result the prior (Neely & Weller 2003) predicted. The SMA 20/50 cross in this
window behaves like a random entry.

Statistical power: with an ~11-pip per-trade s.d., a year (≈270 trades) only
resolves expectancy to about ±1.3 pips/trade. Detecting a real 0.5-pip edge
would need ≈1,900 trades, about 7 years of data. One year can rule out a large
edge but not a small one.

## Decision
**discard** (as configured).
**Why:** expectancy CI [−1.20, +1.42] straddles zero; TP rate 40.9% vs 40% null; H1
negative / H2 positive; ex-November the total is −46.7. Tuning SL/TP cannot fix this:
under a random-walk entry every bracket has expectancy ≈ −costs (Kaminski & Lo
2014). Any next variant must change the *entry* idea, not the exits.


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
