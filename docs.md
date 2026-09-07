# FX Backtester — Usage

Companion to [`fx_backtester_spec.md`](fx_backtester_spec.md). The spec says *why*
each decision was made; this doc shows *how* to use each component once it exists.

**Status legend:** ✅ built · 🚧 in progress · 📋 planned (API from the spec, may
still shift) · ⏸️ deferred (not this build)

| Module | Purpose | Status |
|---|---|---|
| `lib/data.py` | Load + sanity-check 1s data, resample to coarser timeframes | ✅ loader · 📋 `resample()` |
| `lib/engine.py` | `Engine` — run a strategy over the data, produce a trade log | 📋 |
| `lib/strategies.py` | Concrete `Strategy` subclasses (SMA crossover first) | 📋 |
| `lib/signals.py` | Pure, composable signal helpers strategies call into | 📋 |
| `lib/evaluate.py` | Normal + adversarial performance metrics | 📋 |
| `lib/viz.py` | Chart/replay visualizer | ⏸️ |

---

## Setup

```bash
# from repo root
python -m venv .venv
.venv\Scripts\activate            # Windows

pip install polars numba numpy matplotlib
```

- **polars** — the entire data layer (no pandas at the data layer).
- **numba** — JITs the inner 1-second fill-resolution loop in the engine.
- **matplotlib** — evaluation charts (equity curve, monthly P&L, MC distributions).

Data files live in `data/` (git-ignored). The 1s EURUSD file is a single CSV with
bid and ask OHLCV side by side:

```
timestamp, bid_open, bid_high, bid_low, bid_close, bid_volume,
           ask_open, ask_high, ask_low, ask_close, ask_volume
```

`timestamp` is an ISO string with a UTC offset (`2024-01-01 22:00:12+00:00`).

---

## `lib/data.py` — data layer ✅ / 📋

The pipeline is three separable steps — the engine reuses the check step on a
frame it was handed (spec §2.1) without re-loading:

```python
read_1s_csv(path)  -> raw pl.DataFrame        # one full read: schema + timestamp parse
normalize_1s(df)   -> (clean df, n_dropped)   # drop exact-duplicate rows, sort
validate_1s(df)    -> None | raises           # the hard §0.5 checks
```

### `FxData` — load, validate, gap report ✅

Constructing the object **is** the validation: it runs all three steps plus the
gap analysis and raises `DataQualityError` on any hard failure. If it returns,
the data is good.

```python
from lib.data import FxData        # or `from data import FxData` if cwd is lib/

data = FxData("../data/EURUSD_1s_2024.csv")   # a path...
data = FxData(existing_polars_df)             # ...or an in-memory DataFrame / LazyFrame
```

```
FxData: ../data/EURUSD_1s_2024.csv
  bars ................. 8,841,601
  span ................. 2024-01-01 22:00 -> 2024-12-31 21:59 UTC
  exact dup rows dropped 8
  inter-bar gap ........ median 1s  p99 19s
  weekend gaps ......... 52
  holiday gaps ......... 8
  unexplained gaps .... 0  (>= 600s)
  largest unexpl. gap . 561s (9.3 min) at 2024-05-12 21:06 UTC
  checks .............. PASSED
```

The `largest unexpl. gap` line is always printed — a hole just under the
reporting threshold is never hidden behind the `0`.

**Attributes:**

| attr | type | meaning |
|---|---|---|
| `.df` | `pl.DataFrame` | cleaned data, sorted by `timestamp` (`Datetime[us, UTC]`) |
| `.gaps` | `pl.DataFrame` | one row per reported gap: `start, end, gap_s, gap_h, kind, start_dow` |
| `.unexplained_gaps` | `pl.DataFrame` | `.gaps` filtered to `kind == "unexplained"` |
| `.gap_summary` | `dict` | span, median/p99 gap, gap counts by kind, largest unexplained gap + start |
| `.n_exact_duplicate_rows_dropped` | `int` | fully-identical rows removed pre-validation |

**Constructor options:**

```python
FxData(
    source,                                   # CSV path | pl.DataFrame | pl.LazyFrame
    timestamp_format="%Y-%m-%d %H:%M:%S%z",   # explicit; %z -> tz-aware UTC
    holidays=None,                            # iterable[date]; None -> fx_holidays() for the data's year span
    gap_report_threshold_s=600,               # gaps >= this land in .gaps
    strict_gaps=False,                        # True -> unexplained gap >= threshold raises
    verbose=True,                             # print the report on construct
)
```

**Checks performed** (all raise `DataQualityError` except gaps):

| check | rule |
|---|---|
| schema | all expected columns present |
| timestamp parse | every row parses with `timestamp_format` (string source only) |
| exact-duplicate rows | dropped silently, counted (the month-boundary download artifact) |
| duplicate timestamps | rows sharing a timestamp but with **different** values → raise |
| nulls | none, any column |
| NaNs | none, any float column (NaN ≠ null in polars — checked separately) |
| OHLC consistency | per side: `high ≥ max(open,close,low)`, `low ≤ min(open,close,high)` |
| negative spread | `ask ≥ bid` on all of O/H/L/C |
| gaps | classified weekend / holiday / unexplained; unexplained ≥ threshold → warn (or raise if `strict_gaps`) |

**Use it in a pipeline:**

```python
data = FxData(path, verbose=False, strict_gaps=True)   # raises on ANY anomaly
df = data.df
```

### `load_1s_data(source, **kwargs) -> pl.DataFrame` ✅

Spec §1's entry point, adapted to the single-file schema. `source` is a CSV path
or an already-loaded `pl.DataFrame` / `pl.LazyFrame`. Returns just the cleaned
frame:

```python
from lib.data import load_1s_data
df = load_1s_data("../data/EURUSD_1s_2024.csv")
```

Use `FxData` directly when you also want the gap report.

### `validate_1s(df) -> None` ✅ — for the engine

The single source of truth for "is this a valid 1s frame". Raises
`DataQualityError` or returns `None`. `engine.py` calls this at construction time
(spec §2.1) instead of re-implementing the checks. The check expressions
(`ohlc_violation_expr(side)`, `negative_spread_expr()`) are also importable if a
call site needs the raw boolean mask.

```python
from lib.data import validate_1s
validate_1s(df)   # in Engine.__init__, on the frame handed in
```

### `analyze_gaps(df, *, holidays=None, report_threshold_s=600) -> (summary, gaps)` ✅

Standalone gap classifier (what `FxData` uses internally). A gap is `weekend`
only if it starts Friday, ends Sat/Sun **and** lasts > 12h; `holiday` if either
endpoint is a `holidays` date; `unexplained` otherwise. `summary` always carries
`max_unexplained_gap_s` / `max_unexplained_gap_start` regardless of threshold.

### `fx_holidays(years)` / `easter_sunday(year)` ✅ — holiday calendar, any year

`holidays=None` (the default) auto-derives the calendar from the data's year
span, so a 2024 file and a 2019–2027 file both get the right dates with no config.

```python
from lib.data import fx_holidays, easter_sunday

fx_holidays(2027)                 # frozenset of 6 dates for one year
fx_holidays(range(2019, 2028))    # union across many years
easter_sunday(2025)               # date(2025, 4, 20) — Good Friday is 2 days earlier
```

Per year: New Year's Day, **Good Friday** (computed via the Gregorian computus —
no dependency, no lookup table), Christmas Eve, Christmas Day, Boxing Day, New
Year's Eve. Deliberately short — FX is 24/5 and merely *thins* for most national
holidays rather than closing. Pass an explicit iterable of `date` to override.

### `resample(df, timeframe) -> pl.DataFrame` 📋

Aggregate the 1s base to a coarser timeframe. All coarser timeframes are **derived
here**, never loaded as separate files.

```python
bars_5m = resample(df, "5m")
bars_1h = resample(df, "1h")
bars_4h = resample(df, "4h")
```

- Bucket convention: `label=left, closed=left` — a bucket at `HH:MM:00` covers
  `[HH:MM:00, HH:MM:00 + timeframe)`.
- Bid **and** ask OHLC preserved separately: `open=first, high=max, low=min,
  close=last` per side.
- Each bar also carries its **close time** = `bucket_start + timeframe` (computed
  from the actual `timeframe`, never a hardcoded +5m — a stale assumption here is
  a lookahead bug).
- The trailing **partial bucket is dropped** if the 1s data doesn't end exactly
  on a timeframe boundary (`bucket_start + timeframe <= max(ts) + 1s`).

---

## `lib/engine.py` — backtest engine 📋

### `Engine`

```python
from engine import Engine

engine = Engine(bars_5m, base_1s=df)   # signal-timeframe bars + 1s base for fills
trades = engine.backtest(strategy)     # -> pl.DataFrame trade log
metrics = engine.evaluate(trades, starting_balance=10_000, lot_size=0.1)
```

`Engine` does **not** load data — hand it an already-cleaned frame. At
construction it calls `data.validate_1s()` on what it was given and fails loudly
if you didn't clean it upstream. It needs the 1s base alongside the
signal-timeframe bars for fill resolution.

### Timing model (enforced by the engine, spec §0.1–0.2)

- A signal computed from bar `t`'s close is acted on at **bar `t+1`'s open** —
  never within the same bar.
- Within a bar: **open first** (signal entries/exits fill here), **then** the
  price moves through the bar's range (SL/TP checked here). A position that exits
  on a signal at the open is not exposed to that bar's intrabar SL/TP.
- **Spread-correct fills:** buys (long entry / short exit) fill at **ask**; sells
  (short entry / long exit) fill at **bid**. Mid-price is for signals only.

### Fill resolution — the 1-second path (spec §2.3)

Once a trade is open, the engine walks the **real 1s price path** between entry
and exit to find the true first-touch of SL or TP — not the signal-timeframe
bar's OHLC range. The inner walk is a `@njit` imperative loop (numba) — fast, but
still reads like a plain step-by-step loop so event ordering stays inspectable.

### Trade log columns (indicative)

`entry_time, entry_price, direction, exit_time, exit_price, pips, exit_reason`

`exit_reason ∈ {sl, tp, opposite_signal, end_of_data}`. An open position at the
end of data is **force-closed** at the last price and tagged `end_of_data` —
never silently dropped.

### Out of scope for the engine

Position sizing (trades are tracked in **pips only**); multi-instrument support
(pip size `0.0001` is hardcoded for EURUSD).

---

## `lib/strategies.py` + `lib/signals.py` — strategies 📋

### `Strategy` interface

```python
from abc import ABC, abstractmethod

class Strategy(ABC):
    sl_pips: float
    tp_pips: float
    exit_on_opposite_signal: bool = True   # also exit when the opposite signal fires

    @abstractmethod
    def generate_signals(self, df):
        """Pure: df in -> df out with (at least) `long_signal` and
        `short_signal` bool columns added. May add any other columns (SMA
        values, trend_direction, session flags) for debugging/viz.

        Responsible for its own no-lookahead correctness: a value at row t may
        only use info available through bar t's close, where 'bar t's close' =
        bar_start + this strategy's timeframe duration (NOT a hardcoded +5m).
        """
```

SL/TP are **constructor params** — they define a strategy variant, not a separate
engine argument.

### First strategy — SMA(20/50) crossover (reference / regression case)

```python
from strategies import SmaCrossoverStrategy

strat = SmaCrossoverStrategy(fast_n=20, slow_n=50, sl_pips=10, tp_pips=20)
trades = engine.backtest(strat)
```

### `signals.py` — composable helpers

Pure functions `generate_signals()` implementations call into. They may leave
intermediate columns behind (SMA values, `trend_direction`, session flags) —
useful for debugging and the deferred visualizer.

```python
from signals import sma_crossover, trend_filter_4h, session_flag

df = sma_crossover(df, fast_n=20, slow_n=50)         # -> long_signal, short_signal, sma_fast, sma_slow
df = trend_filter_4h(df, base_4h)                    # -> trend_direction  (lookahead-safe merge_asof)
df = session_flag(df, "London", tz="Europe/London")  # -> in_london_session  (DST-aware)
```

> **Session flags & DST:** derive session membership from the London-local *hour*
> (`.dt.convert_time_zone("Europe/London")`), not a fixed UTC hour — the London
> open is 08:00 UTC in winter but 07:00 UTC in summer.

---

## `lib/evaluate.py` — evaluation 📋

Exposed as `Engine.evaluate(trades_df, ...)`. Both tiers are built together.

```python
metrics = engine.evaluate(
    trades,
    starting_balance=10_000,
    lot_size=0.1,
    exclude_best_month=True,
    exclude_best_trades_pct=0.05,
    bootstrap_n=10_000,
    mc_shuffles=10_000,
)
```

### Normal metrics (§3.1)

Equity curve (pips + \$), max drawdown (% and trough date), Sharpe & Sortino
(annualized from daily returns, rf=0), MAR (CAGR / max DD), win rate, expectancy
(pips/trade), profit factor, avg win/loss, monthly P&L table + bar chart.

### Adversarial metrics (§3.2) — always present, not optional

| metric | question it answers |
|---|---|
| Bootstrap CI on win rate & expectancy | how precise is the edge estimate? (resampled, not normal-approx) |
| Monte Carlo trade-order shuffle | was the reported drawdown just a lucky sequence? (reports DD distribution: median / 95th / worst) |
| P&L excluding best month | does the result hinge on one lucky stretch? |
| P&L excluding best N% of trades | same, at trade level |
| Gross vs net cost decomposition | "edge was real but costs ate it" vs "no edge" |
| Sample-size warning | below ~100 trades, precision is low — flagged prominently, verdict withheld |

> The MC shuffle tests **sequence risk on the trades you already have** — it can't
> detect an edge that doesn't exist. A good shuffle distribution is not validation
> of the strategy.

---

## `lib/viz.py` — visualizer ⏸️

Deferred — not part of this build. Planned: `Strategy.visualize(df)` thin
delegator, `lightweight-charts-python` renderer, replay controls, point-style vs
region-style signal rendering from explicit per-strategy column lists. See spec §5.

---

## End-to-end (once the engine lands)

```python
from lib.data import load_1s_data, resample
from lib.engine import Engine
from lib.strategies import SmaCrossoverStrategy

df       = load_1s_data("../data/EURUSD_1s_2024.csv")
bars_5m  = resample(df, "5m")

engine   = Engine(bars_5m, base_1s=df)
strat    = SmaCrossoverStrategy(fast_n=20, slow_n=50, sl_pips=10, tp_pips=20)

trades   = engine.backtest(strat)
metrics  = engine.evaluate(trades, starting_balance=10_000, lot_size=0.1)

print(metrics["summary"])
```

---

## Testing (spec §6)

```bash
pytest lib/tests/
```

- **`test_data.py`** ✅ (21 tests) — synthetic-frame tests for every hard check
  (clean data passes; conflicting duplicate timestamp / broken OHLC / negative
  spread / null / NaN / missing column each raise), the gap classifier (weekend
  size guard, holiday, fabricated mid-week hole), the per-year holiday calendar
  (Easter computus, auto-derived from data span for an arbitrary year), and that
  a sub-threshold hole still shows in the report.
- **Regression:** SMA(20/50) on resampled 5m bars. Baseline from the prototype was
  **1,691 trades, −346.5 pips, 33.0% win rate** (old same-bar fill approximation).
  Expect **trade count, entry timestamps/prices, and result shape** (small
  negative edge) to match closely — **not** the exact pip total (the new engine
  resolves fills on the real 1s path). A materially different trade count, a sign
  flip, or a wild pip swing = real bug, investigate.
- **Boolean-dtype regression:** a crossover helper must return real `bool` dtype
  and a sane signal count on a synthetic series — guards the `.shift(1)` →
  `object`-dtype → bitwise-`~` bug that once inflated the signal count 44×.
- **`resample()` lookahead tests:** (a) trailing partial bucket dropped when the
  data doesn't end on a boundary; (b) for several `timeframe` values, close time =
  `bucket_start + timeframe`, not a hardcoded duration.
