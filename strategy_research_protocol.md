# Strategy Research Protocol

**Audience: an AI agent (any model/session) doing strategy research in this
repo.** This is not a spec for a feature to build — the framework is already
built and tested (see `docs.md`). This is the *process* to follow when using
it to develop and evaluate trading strategies, so that:

1. nothing gets reimplemented ad hoc when the tested framework already does it,
2. every hypothesis and result is written down **before** it can be forgotten
   or silently rationalized after the fact, and
3. a human (or a different agent, in a different session) can always
   reconstruct *why* a strategy was kept, changed, or dropped — months later,
   without re-deriving it from scratch.

If you are an agent reading this at the start of a research session: read
this whole document first, then skim `research/journal.md` for what's already
been tried before writing any new code. Don't repeat an experiment that's
already logged as failed without saying explicitly why you think it's worth
retrying.

---

## 0. Orient yourself first

- **`docs.md`** — the full usage reference for every component (`lib/data.py`,
  `lib/engine.py`'s `Strategy`/`Engine`, `lib/evaluate.py`, `fx_viz`). Read the
  relevant sections before writing code that duplicates what's already there.
- **`fx_backtester_spec.md`** — the *why* behind the engine's timing/fill rules
  (§0.1–§0.4 no-lookahead model). These rules are not optional style
  preferences — the whole regression saga (`regression.md`) exists because
  getting them wrong silently produces a backtest that lies to you.
- **`lib/` is the tested, stable core.** `lib/data.py`, `lib/engine.py`,
  `lib/evaluate.py` are validated (157 tests, see `docs.md`'s Testing
  section) and should not be modified for a one-off strategy experiment. If a
  strategy genuinely needs new framework capability (e.g. a new signal
  primitive), that's a deliberate, separate decision — flag it to the human
  rather than quietly extending `lib/` mid-experiment.
- **`lib/strategies.py`** holds only **graduated** strategies — ones that
  survived the full evaluation in §3 below and are considered reference
  implementations. Day-to-day experimentation does not happen there (§1).

---

## 1. Folder structure for research

```
research/
  journal.md                     <- the index: one line per experiment, newest last
  strategies/
    001_sma_cross_baseline.py    <- one file per strategy variant, numbered + named
    002_rsi_mean_reversion.py
    ...
  runs/
    001_sma_cross_baseline/
      summary.md                 <- the full write-up for this run (template in §4)
      equity.png
      monthly.png
      mc_drawdown.png
    002_rsi_mean_reversion/
      ...
```

- **Number strategies sequentially** (`001`, `002`, …), never reuse a number,
  never delete a folder — including for strategies that failed. A failed
  experiment with a clear write-up of *why* it failed is exactly what prevents
  someone (human or agent) from re-trying the same dead end in six months.
- A strategy file in `research/strategies/` is a normal `Strategy` subclass
  (see §5 for the skeleton) — nothing framework-specific about where it lives,
  it's imported the same way `lib.strategies.SmaCrossoverStrategy` is.
- **Promotion**: once a strategy is genuinely decided as a keeper (§3's
  criteria), move/copy it into `lib/strategies.py` as a proper reference
  strategy, and say so explicitly in both the run's `summary.md` and
  `journal.md`. Keep the original numbered file in `research/strategies/` too
  — the journal entry should link both.

---

## 2. The workflow, in order

**Do not skip or reorder these steps.** Step 1 in particular is the one most
tempting to skip — resist that; it's the entire point of this protocol.

1. **Write the hypothesis before writing any code.** One or two sentences:
   what market behavior is this strategy trying to capture, and why would it
   plausibly make money? If you can't state this, you're about to p-hack a
   parameter sweep instead of testing an idea — stop and reconsider. Put this
   in the run's `summary.md` (§4) under "Hypothesis" *first*, then implement.
2. **Implement as a `Strategy` subclass** in `research/strategies/NNN_name.py`
   (skeleton in §5). Reuse `lib/signals.py`'s helpers where they fit; add new
   pure, composable signal functions there if a genuinely new primitive is
   needed (not strategy-specific logic — that stays in `generate_signals`).
3. **Backtest and evaluate through the engine** — never hand-roll P&L,
   drawdown, or win-rate math. `Engine.backtest(strategy)` → trade log,
   `engine.evaluate(trades, ...)` → the full report (see `docs.md`'s
   `Engine.evaluate` section for the exact return shape).
4. **Always run the full adversarial suite, not just the headline numbers.**
   `report["verdict"]`, `report["adversarial"]["gross_vs_net"]`,
   `["bootstrap_ci"]`, `["mc_drawdown"]`, `["sample_size"]` — all of them,
   every time. A strategy that only gets judged on net pips/win rate is
   exactly the failure mode this framework was built to resist (see
   `fx_backtester_spec.md`'s framing of "the backtest lied to me"). §3 below
   is how to actually read these.
5. **Visualize before trusting any number.** `strategy.visualize(engine,
   show_trades=True)` and look at real trades — entries lining up with real
   crossovers, SL/TP boxes at sane levels, no suspicious repeated patterns.
   This is not optional polish: in this exact project, eyeballing real
   `PositionTool` overlays this way is what caught a genuine rendering bug
   that silently made trades look wrong. A backtest number you haven't looked
   at on a real chart is a number you don't actually trust yet. Remember
   timeframe-switching on the chart is **display-only** — it does not
   re-backtest, so compare trades against the strategy's own configured
   timeframe, not whatever's currently selected in the topbar.
6. **Write the run's `summary.md`** (template in §4) and **append one line to
   `research/journal.md`.** Do this even — especially — if the strategy
   failed. An entry is written exactly once per run and is never edited to
   look better in hindsight; if you rerun with changed parameters, that's a
   new numbered entry, not an edit to the old one.
7. **Make an explicit decision**: keep exploring (what's the next variant and
   why), promote to `lib/strategies.py` (§1, §3), or discard (say why,
   specifically — "noisy edge" is not as useful a reason as "bootstrap CI for
   expectancy spans [-0.4, +0.3] pips, straddles zero, no real edge").

---

## 3. How to interpret the results (the actual metrics this framework produces)

Don't eyeball net pips and stop there. In order of how much they should move
your decision:

- **`report["verdict"]`** — sample-size-gated. If trade count is below the
  threshold, the verdict is **withheld even if net pips look great** — a
  "looks great" based on 40 trades is noise, not a signal. Respect the
  withholding; don't report a verdict the framework itself says isn't
  trustworthy yet.
- **`bootstrap_ci`** (on win rate and expectancy) — if the expectancy CI
  **straddles zero**, there is no statistically real edge in either
  direction, regardless of how the point estimate looks. This is usually the
  single most important number here.
- **`gross_vs_net`** — decomposes P&L into the edge before costs and the
  spread/cost drag. "Gross positive, net negative" means a real edge exists
  but costs ate it (a sizing/frequency/instrument problem, potentially
  fixable). "Gross negative" means there's no edge to begin with (a strategy
  logic problem — don't try to fix this by reducing costs).
- **`mc_drawdown`** — reshuffles trade order and compares the real drawdown to
  the distribution. If the real drawdown is unusually bad vs. reshuffled
  orderings (flagged "fragile"), the reported risk is partly a lucky/unlucky
  *ordering* artifact, not a stable property of the strategy — don't size a
  position off a drawdown number that isn't ordering-robust.
- **`ex_best_month` / `ex_best_trades`** — if removing the single best month
  or the best few trades flips the result from profitable to not, the edge is
  concentrated in a small number of outlier events, not a repeatable process.
  Flag this explicitly even if the headline number looks fine.

A strategy only earns real confidence when: the verdict isn't withheld, the
bootstrap CI doesn't straddle zero, the edge survives gross-vs-net, and the
drawdown isn't flagged fragile. Any one of these failing is worth a line in
the journal even if you decide to keep iterating anyway — note what failed,
not just the final verdict.

---

## 4. `summary.md` template (copy this into every `research/runs/NNN_name/summary.md`)

```markdown
# 00N — <strategy name>

**Date:** <YYYY-MM-DD>
**File:** research/strategies/00N_<name>.py
**Status:** exploring | promoted | discarded

## Hypothesis
<1-2 sentences, written BEFORE running the backtest>

## Parameters
<the actual constructor args used for this run>

## Headline result
- trades: <n>, win rate: <%>, net pips: <±n>
- verdict: <framework's verdict, or "withheld — sample size">

## Adversarial checks
- gross vs net: <numbers + 1-line reading>
- bootstrap CI (expectancy): <[lo, hi]> — <straddles zero? / real edge?>
- MC drawdown: <fragile? / robust?>
- ex-best-month / ex-best-trades: <concentrated or repeatable?>

## Visual check
<what you saw in strategy.visualize(engine, show_trades=True) — anything
suspicious about entries/exits/box sizes? did you check at the strategy's
OWN timeframe, not a different display timeframe?>

## Interpretation
<plain-English judgment — what do these numbers actually mean for whether
this idea has a real edge>

## Decision
<keep exploring (+ next variant) | promote to lib/strategies.py | discard>
**Why:** <the actual reasoning, specific to this strategy's numbers — not a
template phrase>
```

And in `research/journal.md`, append one line (newest last, never reordered):

```markdown
- **00N** `<name>` (<date>) — <hypothesis in ~10 words> → <decision + 1-line why>. [details](runs/00N_<name>/summary.md)
```

---

## 5. `Strategy` subclass skeleton

```python
from __future__ import annotations
import polars as pl
from lib.engine import Strategy
from lib.signals import sma, crossover   # reuse existing primitives where they fit

class MyStrategy(Strategy):
    # chart-rendering declarations (optional, for strategy.visualize() —
    # undeclared columns are simply not plotted, never guessed at)
    line_columns: list[str] = []
    marker_columns: list[str] = []
    region_columns: list[str] = []

    # only set this True if the idea genuinely requires "always in the
    # market" — most new strategies should leave it False and go flat
    # between signals
    reverse_on_opposite_signal: bool = False

    def __init__(self, *, sl_pips: float, tp_pips: float, timeframe: str = "5m", **params):
        super().__init__(sl_pips, tp_pips, timeframe)
        # ... store your own params ...

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        # PURE: don't mutate df, return a new frame.
        # Must add long_signal/short_signal as real pl.Boolean columns.
        # No-lookahead is YOUR responsibility here: row t may only use
        # information available through bar t's close (fx_backtester_spec.md
        # §0.1-§0.4) — the engine enforces the t+1 ACTION timing separately,
        # but it trusts your signal computation not to peek ahead.
        ...
```

```python
# running it
from lib.data import load_1s_data, resample
from lib.engine import Engine

raw    = load_1s_data("data/EURUSD_1s_2024.csv")
engine = Engine(resample(raw, "5m"), raw)

strat  = MyStrategy(sl_pips=10, tp_pips=20)
trades = engine.backtest(strat)
report = engine.evaluate(trades, starting_balance=10_000, pip_value=1.0, seed=0)

print(report["verdict"])
print(report["adversarial"]["bootstrap_ci"])
print(report["adversarial"]["mc_drawdown"])

chart = strat.visualize(engine, show_trades=True)   # look before you trust
```

---

## 6. Hard rules (do not violate these to make a result look better)

- Never compute P&L, win rate, or drawdown outside `lib/evaluate.py` — if the
  built-in metrics don't answer a question you have, add a function there
  (and test it), don't compute it ad hoc in a notebook cell.
- Never silently drop the adversarial checks because the headline number
  already looks good — the entire point of this framework is that headline
  numbers lie.
- Never edit a past `journal.md`/`summary.md` entry to match a later,
  different result. Append a new numbered entry instead.
- Never let `generate_signals` use information from after bar `t`'s close for
  row `t` — this is the single most common way a backtest silently cheats.
  If unsure, check it the way `test_regression.py` does: confirm `entry_time`
  is one bar after a real crossover edge, not on the same bar as the edge.

## Standing rule (user, 2026-10-07): "Who is losing money so that I can make money?"
Every idea and every pre-registration starts with a **Who loses, and why** section: name the counterparty
(e.g. stop-loss orders, hedgers, benchmark flows, slow or over-reacting traders) and why they keep paying us.
Count the costs too: spread and commission go to market makers and the prop firm on every trade.
An idea with no named loser is flagged before any test.

## Standing rule (user, 2026-10-07): the setup template
Every setup is written and tested in this structure:

| # | Element | Question | In code |
|---|---|---|---|
| 0 | Who loses, and why | Who is on the other side at this POI, and why do they lose? | (written rationale) |
| 1 | Context | Trending up / down / range? | a state label on higher timeframes |
| 2 | Bias | Which way do we expect price to go? | long only / short only / both |
| 3 | POI | Where (level) and when (time window) do we pay attention? | level + session window |
| 4 | Confirmation | What must happen at the POI before we act? | lower-timeframe trigger |
| 5 | Execution & management | Entry, stop, target, stall handling, size, prop-firm rules | engine columns + rules |

Build one layer at a time: **POI alone first**, then add confirmation, then context, then bias (hardest; every
direction-prediction attempt so far failed). Keep a layer only if it improves results in both practice years.
Pass bars include a minimum R per trade or a confidence-interval condition, not just "positive" (lesson from 059).

## Standing rule (user, 2026-10-07): FTMO prop-firm mode
The user trades FTMO's cheapest account (Standard). Every run from now on:
- **News:** FTMO's window, no position open from 2 minutes before to 2 minutes after a red release for the pair's
  currencies (`apply_news_blackout`, default `FTMO_NEWS_MIN = 2`; replaces the earlier ±60 min used in 045–065).
- **No overnight, weekend or rollover holding:** `run_experiment --prop` / `Engine.backtest(..., prop=PropConfig())`
  forces flat by 16:55 New York, blocks entries 16:55–17:00, and charges $5/lot round-trip commission (0.5 pip).
- **Scorecard:** `lib.prop.simulate_challenge` (FTMO 2-step) pass probability at several risk levels, next to a
  zero-edge twin of the same strategy (`demean=True`).

## Standing rule (user, 2026-10-07): target = FTMO 1-step, $10k
All strategies are built for and judged on **FTMO 1-step $10k**: one +10% target; −3% daily loss; −10% max loss trailing
the highest end-of-day balance; best day ≤ 50% of total positive-day profit; 90% split; fee ≈ $89 (€79).
- Backtests: `run_experiment --prop` (±2 min news, flat by 16:55 NY, $5/lot commission until the user confirms the real figure).
- Scorecard: `lib.prop_firms.ftmo_1step_scorecard(trades, start, end)` on the strategy's own trades: average $ per
  attempt, pass rate, trades/days to pass and until money received > fee, next to the zero-edge twin.
- Design implications: keep daily risk well inside 3% (one or two trades a day at ~1%, own daily stop ~1.2%);
  avoid lumpy profit (one big day > 50% of profits blocks the pass); steady, many small independent trades suit it.
