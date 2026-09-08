# FX Backtester — Usage

Companion to [`fx_backtester_spec.md`](fx_backtester_spec.md). The spec says *why*
each decision was made; this doc shows *how* to use each component once it exists.

**Status legend:** ✅ built · 🚧 in progress · 📋 planned (API from the spec, may
still shift) · ⏸️ deferred (not this build)

| Module | Purpose | Status |
|---|---|---|
| `lib/data.py` | Load + sanity-check 1s data, resample to coarser timeframes | ✅ |
| `lib/engine.py` | `Strategy` ABC · `Engine` · `_resolve_exit` 1s SL/TP walk | ✅ `Strategy`, `_resolve_exit` · 🚧 `Engine` (5a: entries) |
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

### `resample(df, timeframe, *, fill_gaps=True) -> pl.DataFrame` ✅

Aggregate the 1s base to a coarser timeframe. All coarser timeframes are **derived
here**, never loaded as separate files.

```python
bars_5m = resample(df, "5m")
bars_1h = resample(df, "1h")
bars_4h = resample(df, "4h")
```

Output columns: `timestamp` (bucket start), `close_time`, `{bid,ask}_{open,high,low,close,volume}`, `n_ticks`.

- Bucket convention: `label=left, closed=left` — a bucket at `HH:MM:00` covers
  `[HH:MM:00, HH:MM:00 + timeframe)`. (`polars.group_by_dynamic`.)
- Bid **and** ask OHLC preserved separately: `open=first, high=max, low=min,
  close=last` per side; volume **summed** per side; `n_ticks` = 1s rows in the
  bucket (`0` ⇒ a filled flat candle).
- Each bar carries **`close_time` = `bucket_start + timeframe`**, derived from the
  actual argument via `offset_by` — never a hardcoded +5m. Treating a 1h bar as
  closed 5 min after it opened is a lookahead bug.
- The trailing **partial bucket is dropped**: any bucket whose `close_time` lands
  after `last_1s_timestamp + 1s` never finished. (The `+1s`: a 1s bar labelled
  `HH:MM:59` covers `[59, 60)`.)

**Sparse-data policy** (`fill_gaps`, default `True`): the 1s feed is sparse — a
quiet window can hold zero ticks and `group_by_dynamic` then emits no bar.
`fill_gaps=True` prints those interior windows as **flat carry-forward candles**
(`O=H=L=C` = prior close, volume `0`, `n_ticks` `0`), TradingView-style —
**except** across a gap ≥ 12h (`WEEKEND_MIN_SECONDS`), left as a true hole.

- *Why fill interior gaps:* strategies index bars positionally ("SMA of the last
  20 bars"). A silently-missing 3 a.m. window makes "20 bars ago" drift in
  wall-clock time and desyncs strategies on different timeframes. A flat bar
  keeps the index honest and barely moves an SMA.
- *Why not fill weekends:* a 48h fill injects ~576 identical Friday-close 5m bars;
  an SMA(50) is then 100% stale for the first hours of Monday and fires a false
  crossover when ticks resume. The market didn't exist — the honest shape is a
  discontinuity, which is what TradingView shows for FX. Same 12h threshold as
  `analyze_gaps`, so "real session break" has one definition.
- `fill_gaps=False` returns only buckets that had ticks — for debugging or
  comparing against an externally-resampled series.

On the real 2024 file: 5m → 74,999 bars (28 filled), 1h/4h → 0 filled (no
tick-free hour within a session all year).

**Known limitations** (reviewed 2026-09-07 — not bugs, safe for the 2024 file):

1. *The 12h fill threshold cuts both ways.* A gap `< 12h` is flat-filled. On a
   different dataset — an 8h broker outage, a regional holiday missing from
   `fx_holidays()` — that would inject dozens–hundreds of stale carry-forward
   bars quietly. None occur in the 2024 file. `n_ticks == 0` marks every filled
   bar, so before trusting signals on new data, check
   `resample(...).filter(pl.col("n_ticks") == 0)` for suspicious runs.
2. *Empty-input schema mismatch.* The early-return path for an empty `df` yields
   a frame without the `close_time` / `n_ticks` columns the normal path adds, so
   a caller selecting those columns crashes only on empty input. One-line fix
   when convenient; edge case.

---

## `lib/engine.py` — backtest engine ✅ `Strategy` · 📋 `Engine`

### `Strategy` (ABC) ✅

The formal strategy interface (spec §2.2). A concrete strategy subclasses it,
calls `super().__init__(sl_pips, tp_pips, timeframe)`, then adds its own params.

```python
from abc import ABC, abstractmethod
import polars as pl

class Strategy(ABC):
    exit_on_opposite_signal: bool = True   # class attr; subclass sets False for SL/TP-only exits

    def __init__(self, sl_pips: float, tp_pips: float, timeframe: str):
        # validates: sl_pips > 0, tp_pips > 0, timeframe a non-empty str (else ValueError)
        ...

    @abstractmethod
    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        """Pure — does not mutate df, returns a new frame with at least
        `long_signal` and `short_signal` added, both real pl.Boolean dtype
        (the engine trusts that — spec §0.4). May add any other columns; the
        engine ignores them. Owns its no-lookahead correctness: row t uses
        only info through bar t's close = bar_start + self.timeframe."""
```

| member | kind | notes |
|---|---|---|
| `sl_pips`, `tp_pips` | instance (ctor) | pip distances, must be `> 0` |
| `timeframe` | instance (ctor) | `"5m"`, `"1h"`, … — drives the "bar t's close" math |
| `exit_on_opposite_signal` | class attr, default `True` | engine also closes on the opposite signal, on top of SL/TP |
| `generate_signals(df)` | abstract | the one thing a subclass must implement |

`Strategy(...)` directly raises `TypeError` (abstract). SL/TP/timeframe are
constructor params because they *define* a strategy variant — not engine-run args.

### `Engine` — 🚧 pass 5a (construction + entry timing)

```python
from lib.engine import Engine

engine = Engine(signal_df, base_1s)    # resampled bars + the 1s base
trades = engine.backtest(strategy)     # -> pl.DataFrame trade log
# metrics = engine.evaluate(trades, ...)   # 📋 later
```

`Engine` does **not** load data — hand it frames cleaned upstream
(`load_1s_data` / `resample`).

- **`__init__(signal_df, base_1s)`** — calls `data.validate_1s(base_1s)` (fails
  loudly with `DataQualityError` if the 1s base wasn't cleaned) and stores it for
  5b's fill walk. Checks `signal_df` has `timestamp`, `close_time` and the 8
  `{bid,ask}_{open,high,low,close}` columns and is timestamp-sorted, else
  `ValueError`.
- **`backtest(strategy)`** — runs `strategy.generate_signals(signal_df)`, then
  **validates** `long_signal`/`short_signal` are present and real `pl.Boolean`
  (`ValueError` otherwise — the §0.4 guard). Walks the bars in plain Python
  (small frame, not the bottleneck — §2.3) and returns a frame of
  `entry_time, entry_price, direction, exit_time, exit_price`.

**5a scope / what's a placeholder:** entries honour the t+1 rule (`long_signal`
on bar *t* → enter at bar *t+1*'s open, via `shift(1, fill_value=False)`) and
spread-correct fills (long → `ask_open`, short → `bid_open`). One position at a
time; a same-direction signal while open is ignored. **Exits are crude**: the
position is closed at the next *opposite* signal's t+1 open (long close →
`bid_open`, short close → `ask_open`); a position still open at end of data is
returned with null `exit_time`/`exit_price`. Pass **5b** replaces the exit logic
with the real SL/TP walk over the 1s path + `exit_on_opposite_signal`.

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

**`_resolve_exit(exit_high, exit_low, start_idx, end_idx, direction, sl_level, tp_level)`** ✅
— the `@njit(cache=True)` walk. `direction` is `+1` long / `-1` short.

- The caller passes the 1s high/low of the side the trade **exits against**
  (§0.3): a long exits by selling → pass the **bid** arrays; a short exits by
  buying → pass the **ask** arrays. The function is side-agnostic.
- long: SL when `exit_low[k] <= sl_level`, TP when `exit_high[k] >= tp_level`;
  short: mirrored. Touches inclusive.
- Returns `(hit_idx, exit_price, reason)` — `reason` `0` none (`hit_idx ==
  end_idx`, price `0.0`), `1` SL, `2` TP. `exit_price` is the **level itself** (a
  resting stop/limit order fills at its price).
- One 1s bar straddling both levels → **SL wins** (the spec's old "assume SL
  first" tie-break, now confined to a single second, so rare and bounded).

**`_sl_tp_levels(direction, entry_price, sl_pips, tp_pips, pip=PIP)`** ✅ (plain,
not njit) → `(sl_level, tp_level)`. long: SL below / TP above entry; short:
mirrored.

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

The `Strategy` ABC lives in [`lib/engine.py`](#libenginepy--backtest-engine---strategy---engine)
(above). Concrete subclasses live here.

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

- **`test_data.py`** ✅ (27 tests) — synthetic-frame tests for every hard check
  (clean data passes; conflicting duplicate timestamp / broken OHLC / negative
  spread / null / NaN / missing column each raise), the gap classifier (weekend
  size guard, holiday, fabricated mid-week hole), the per-year holiday calendar
  (Easter computus, auto-derived from data span for an arbitrary year), a
  sub-threshold hole still shows in the report, and `resample` (bid+ask OHLC on
  hand-checked rows, trailing-partial-bucket drop/keep, `close_time` per
  timeframe, flat-candle gap fill, weekend gap left unfilled).
- **`test_engine.py`** ✅ (30 tests) — **Strategy** (9): abstract
  (`Strategy(...)` → `TypeError`); subclass stores `sl_pips`/`tp_pips`/`timeframe`
  + own params; `exit_on_opposite_signal` default/override; `__init__` rejects
  `sl_pips=0` / `tp_pips=-5` / empty or non-str `timeframe`; `generate_signals`
  returns `pl.Boolean` columns and doesn't mutate input. **Engine 5a** (10):
  `__init__` validates `base_1s` (`DataQualityError`), rejects a `signal_df`
  missing columns or unsorted; `backtest` rejects non-Boolean signals; long enters
  at bar t+1 `ask_open`, short at `bid_open`, signal on the last bar → no entry,
  a 2nd same-direction signal while open is ignored, entry timestamp is strictly
  after the signal bar, placeholder exit closes on the opposite signal at `bid_open`.
  **`_resolve_exit` / `_sl_tp_levels`** (11): njit-compiled (`CPUDispatcher`,
  nopython signature); long SL / long TP / neither / same-bar-straddle → SL wins;
  short SL on ask-high, short TP on ask-low; `start_idx` hides earlier touches;
  `_sl_tp_levels` long/short above-below and the `PIP` offset.
- **Regression:** SMA(20/50) on resampled 5m bars. Baseline from the prototype was
  **1,691 trades, −346.5 pips, 33.0% win rate** (old same-bar fill approximation).
  Expect **trade count, entry timestamps/prices, and result shape** (small
  negative edge) to match closely — **not** the exact pip total (the new engine
  resolves fills on the real 1s path). A materially different trade count, a sign
  flip, or a wild pip swing = real bug, investigate.
- **Boolean-dtype regression:** a crossover helper must return real `bool` dtype
  and a sane signal count on a synthetic series — guards the `.shift(1)` →
  `object`-dtype → bitwise-`~` bug that once inflated the signal count 44×.
- **`resample()` lookahead tests:** ✅ in `test_data.py` — (a) trailing partial
  bucket dropped when the data doesn't end on a boundary, kept when it does;
  (b) for 5m and 1h, `close_time == bucket_start + timeframe`, not a hardcoded
  duration; (c) bid/ask OHLC aggregation checked on a few hand-verifiable rows.
