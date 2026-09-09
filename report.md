# FX Backtester — Status Report

_As of commit `bd9d387` ("FInal base framework")._

## TL;DR

**The base framework is complete, committed, and validated end-to-end** against
the real 2024 EURUSD 1-second data. Every component in the spec is built except
the visualizer (§5), which the spec explicitly defers.

- **141 tests pass** (135 fast + 6 `-m slow` end-to-end).
- **§6 regression: PASSED** — the new engine reproduces the prototype's headline
  numbers within tolerance.
- ~1,750 lines of hand-rolled library code (no vectorbt/backtrader) — every
  timing and execution decision is visible and unit-tested.
- One finding worth flagging: the reference `SmaCrossoverStrategy(20/50)` **loses
  money after costs on 2024, and has no statistically distinguishable edge**
  either way. The framework surfaces that clearly — which is the point.

---

## What's built

| Module | Status | Summary |
|---|---|---|
| `lib/data.py` | ✅ | Load the 1s CSV; §0.5 sanity checks (duplicate timestamps, nulls, per-side OHLC consistency, negative spread, gap classification with a computed per-year FX holiday calendar); `resample()` to any timeframe with TradingView-style flat-fill of intra-session gaps and correct trailing-partial-bucket drop. |
| `lib/engine.py` | ✅ | `Strategy` ABC + `Engine`. Rising-edge entries acted on at bar t+1 (§0.1); spread-correct fills, buy@ask / sell@bid (§0.3); each trade's exit resolved on the **real 1-second price path** via a numba `@njit` loop (§2.3) — SL/TP first-touch **raced against** an opposite-signal exit with the §0.2 within-bar ordering enforced; end-of-data force-close (§2.4); optional stop-and-reverse chain. Trades never overlap in wall-clock time. `Engine.evaluate()` is the one-call report. |
| `lib/signals.py` | ✅ | `sma` (null warmup — never a partial average) and `crossover` — the §0.4 boolean-safety function (real `pl.Boolean`, no object-dtype trap, no spurious signal at the SMA warmup boundary). 4H trend-filter and session-flag helpers are stubbed for a later strategy that needs them. |
| `lib/strategies.py` | ✅ | `SmaCrossoverStrategy(fast_n, slow_n, sl_pips, tp_pips, timeframe)` — the reference / regression strategy. Mid price for signals (§0.3), reverses on the opposite cross like the prototype. Keeps `mid_close`/`sma_fast`/`sma_slow` columns for debugging (§4). |
| `lib/evaluate.py` | ✅ | **§3.1 normal metrics** (`evaluate`): win rate, expectancy, profit factor, avg win/loss, total return, signed max drawdown + trough date, annualized Sharpe/Sortino (rf=0), MAR, equity curve, monthly breakdown. **§3.2 adversarial** (all mandatory, all present): gross-vs-net cost decomposition, P&L ex-best-month, P&L ex-best-N%-trades, sample-size-gated verdict, bootstrap CIs on win rate & expectancy (`bootstrap_ci`), Monte-Carlo trade-order shuffle → drawdown distribution + fragility flag (`mc_drawdown`). Both resampling functions are numpy-vectorized and seedable. **Plots**: `plot_equity` / `plot_monthly` / `plot_mc_drawdown` — matplotlib is lazy-imported so headless code never pays for it. |
| `lib/viz.py` (§5) | ⏸️ deferred | Not part of this build, per the spec. |

---

## The §6 regression

**Baseline (prototype):** 1,691 trades · −346.5 pips · 33.0% win rate
(5-min bars, old "assume SL first" same-bar fill approximation).

**This engine (`sl=10 / tp=20`):**

| metric | baseline | this build | §6 tolerance |
|---|---|---|---|
| trade count | 1,691 | 1,714 (+1.4%) | ±5% ✓ |
| win rate | 33.0% | 32.5% | ±3 pts ✓ |
| total pips | −346.5 | −453.1 (1.31×) | sign + 0.5×–2× ✓ |
| wall-clock overlaps | — | 0 | 0 ✓ |

**Verdict: PASS, with one caveat.** The prototype's exact `sl`/`tp` were never
recorded, so they had to be fitted. Key points from the investigation
(`notebooks/regression.ipynb` + `regression.md`):

- **Trade count matches at *any* `sl`/`tp`** (1,700–1,733 across a 25-cell sweep)
  — it's fixed by the crossover count, which validates the signal, entry-timing,
  and reversal logic against the prototype.
- A fitted cell (`mid, sl≈8 / tp≈15`) reproduces −346 pips within ~1% on all
  three metrics.
- The pip gap at the arbitrary `10/20` is a **parameter mismatch, not a bug** —
  the "coarser fill resolution" hypothesis was falsified (0 of 271 TP trades
  would flip to SL under the prototype's 5m-bar rule).
- The regression test locks the current headline numbers so an accidental engine
  change is caught.

---

## What the framework says about the reference strategy (2024 EURUSD)

`SmaCrossoverStrategy(20/50, sl 10 / tp 20)` — **a losing strategy after costs:**

- **Net −453 pips / −4.5% return**, 32.5% win rate, max drawdown −8.9%.
- **Gross vs net:** gross P&L before spread is only **+145 pips** over 1,714
  trades; the **598 pips of spread cost** is what makes it a net loser
  ("edge existed, costs ate it") — but +145 gross is barely above noise.
- **Bootstrap 95% CI on expectancy: [−0.73, +0.22] pips/trade** — straddles
  zero. There is no statistically real edge in either direction.
- **Monte-Carlo drawdown:** not fragile — the historical −8.9% drawdown is, if
  anything, slightly worse than a typical reordering (median −6.8%), so the
  reported risk isn't a lucky-ordering artifact.
- Excluding the single best month (Nov, +291) takes the result to −744 pips.

This is the framework doing its job: it actively resists the "backtest lied to
me" failure mode rather than just warning about it in prose (spec §3 priority).

---

## Test coverage (141 tests)

| file | tests | covers |
|---|---|---|
| `test_data.py` | 27 | every hard sanity check raises; gap classifier; per-year holiday calendar (Easter computus); `resample` OHLC/bucketing/gap-fill on hand-checked rows |
| `test_engine.py` | 49 | `Strategy` ABC; the numba SL/TP walk (long/short, ties, §0.2 ordering); entry timing; every exit path incl. reversal chains; `spread_pips_paid` |
| `test_signals.py` | 8 | `sma` warmup; `crossover` exact bar indices; the §0.4 boolean-dtype regression |
| `test_strategies.py` | 13 | constructor validation; signals use mid not bid/ask; warmup; one hand-built crossover; engine smoke |
| `test_evaluate.py` | 38 | §3.1 scalars vs hand computation; §3.2 gross-vs-net / ex-best-month / ex-best-N / sample-size gate; bootstrap & MC determinism + edge cases; `Engine.evaluate` orchestration; plots return Figures |
| `test_regression.py` | 6 | `-m slow` — full end-to-end §6 regression; skipped if the data file is absent |

---

## Artifacts

- `docs.md` — the how-to-use reference for every component (kept current).
- `regression.md` + `notebooks/regression.ipynb` — the §6 investigation (SL/TP
  sweep, signal-price comparison, pip-gap decomposition).
- `notebooks/full_report.ipynb` — the whole framework running end-to-end:
  load → resample → strategy → backtest → evaluate → the three plots.

## How to run

```bash
pip install polars numba numpy matplotlib
pytest lib/tests/              # 135 fast tests
pytest lib/tests/ -m slow      # + the 6 end-to-end regression tests
```

```python
from lib.data import load_1s_data, resample
from lib.engine import Engine
from lib.strategies import SmaCrossoverStrategy

df     = load_1s_data("data/EURUSD_1s_2024.csv")
engine = Engine(resample(df, "5m"), df)
trades = engine.backtest(SmaCrossoverStrategy(fast_n=20, slow_n=50, sl_pips=10, tp_pips=20))
report = engine.evaluate(trades, starting_balance=10_000, pip_value=1.0, seed=0)

print(report["verdict"], report["summary"])
```

---

## Open items / next steps

1. **§5 visualizer** (`viz.py`) — deferred by the spec; `lightweight-charts`
   replay UI, decoupling what's displayed (1s candles) from what's traded
   (resampled signals).
2. **Nail down the prototype's `sl`/`tp`** if the original numbers can be
   recovered — would turn the regression from "PASS with a fitted parameter"
   into an exact match.
3. **A 4H-trend-filter strategy** is the first place the `join_asof` +
   "bar t's close = bar_start + timeframe" no-lookahead machinery actually
   bites (it's vacuous for the position-based SMA crossover).
4. **`Engine.evaluate` is a plain method** — trivial to expose a CLI or batch
   sweep on top if that's wanted.
