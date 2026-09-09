# FX Backtester — Usage

Companion to [`fx_backtester_spec.md`](fx_backtester_spec.md). The spec says *why*
each decision was made; this doc shows *how* to use each component once it exists.

**Status legend:** ✅ built · 🚧 in progress · 📋 planned (API from the spec, may
still shift) · ⏸️ deferred (not this build)

| Module | Purpose | Status |
|---|---|---|
| `lib/data.py` | Load + sanity-check 1s data, resample to coarser timeframes | ✅ |
| `lib/engine.py` | `Strategy` ABC · `Engine` (`backtest`) · `_resolve_exit` 1s SL/TP walk | ✅ |
| `lib/strategies.py` | Concrete `Strategy` subclasses | ✅ `SmaCrossoverStrategy` |
| `lib/signals.py` | Pure, composable signal helpers strategies call into | ✅ `sma`, `crossover` · 📋 trend filter, session flag |
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
    exit_on_opposite_signal: bool = True     # also close on the opposite signal (on top of SL/TP)
    reverse_on_opposite_signal: bool = False  # ...and immediately re-open the other way

    def __init__(self, sl_pips: float, tp_pips: float, timeframe: str):
        # validates: sl_pips > 0, tp_pips > 0, timeframe a non-empty str;
        # reverse_on_opposite_signal requires exit_on_opposite_signal  (else ValueError)
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
| `reverse_on_opposite_signal` | class attr, default `False` | on an opposite-signal exit, re-open the other way at the same open ("always in the market"); requires `exit_on_opposite_signal` |
| `generate_signals(df)` | abstract | the one thing a subclass must implement |

`Strategy(...)` directly raises `TypeError` (abstract). SL/TP/timeframe are
constructor params because they *define* a strategy variant — not engine-run args.

### `Engine` — ✅ `backtest` complete

```python
from lib.engine import Engine

engine = Engine(signal_df, base_1s)    # resampled bars + the 1s base
trades = engine.backtest(strategy)     # -> pl.DataFrame trade log
# metrics = engine.evaluate(trades, ...)   # 📋 later
```

`Engine` does **not** load data — hand it frames cleaned upstream
(`load_1s_data` / `resample`).

- **`__init__(signal_df, base_1s)`** — calls `data.validate_1s(base_1s)` (fails
  loudly with `DataQualityError` if the 1s base wasn't cleaned). Checks
  `signal_df` has `timestamp`, `close_time` and the 8
  `{bid,ask}_{open,high,low,close}` columns and is timestamp-sorted, else
  `ValueError`. Then **caches the 1s path once** as plain numpy
  (`_ts_ns`, `_bid_high/low/close`, `_ask_high/low/close`) so the per-trade walk
  doesn't rebuild arrays.
- **`backtest(strategy)`** — runs `strategy.generate_signals(signal_df)`,
  **validates** `long_signal`/`short_signal` are present + real `pl.Boolean`
  (`ValueError` — the §0.4 guard) and that no bar has both True (ambiguous →
  `ValueError`). Walks the bars in plain Python (small frame — §2.3).

**Entries** — rising edge only: `long_signal & ~long_signal.shift(1, fill_value=False)`,
acted on at bar *t+1*'s open, long → `ask_open` / short → `bid_open` (§0.3).

**Exits** — resolved on the 1s path from `searchsorted(_ts_ns, entry_ns)` (the
entry second is exposed to its own range, §0.2). Three things race:

- **SL / TP** — `_sl_tp_levels` → `_resolve_exit` on the exit-against side
  (long → bid, short → ask). Touch → `exit_reason "sl"`/`"tp"`, `exit_price` =
  the level.
- **opposite signal** (only if `strategy.exit_on_opposite_signal`) — the first
  opposite rising edge after entry, acted on at *its* bar's t+1 open (long close
  → `bid_open`, short → `ask_open`). The walk's `end_idx` is that open's second
  **exclusive**, so an SL/TP that only prints on the signal-exit bar itself does
  **not** steal the exit (§0.2 — the exact ordering the prototype once got
  wrong). If SL/TP fired on an *earlier* bar, it wins; otherwise the signal exit
  does, `exit_reason "opposite_signal"`.
- **end of data** — nothing else fired → force-close (§2.4),
  `exit_reason "end_of_data"`, `exit_price` = last `bid_close`/`ask_close`.

**Reversal** (`strategy.reverse_on_opposite_signal`) — when a trade exits
`opposite_signal`, the engine immediately opens the opposite position at that
same bar/open (`entry_time == previous exit_time`, `entry_price == previous
exit_price` — the close and the re-open are one spread crossing). The chain
keeps flipping until a trade exits via SL/TP/end-of-data. Off → today's
close-to-flat behaviour, untouched. (One trade's resolution lives in a
`resolve(entry_bar, direction)` helper; `backtest` loops: find an edge → resolve
→ feed a reversal back in, or jump `t` and continue.)

After a non-reversing exit the scan resumes at the first signal bar **at/after
`exit_time`** (`t = max(t+1, searchsorted(sig_ts_ns, exit_ns))`), so **trades
never overlap in wall-clock time** and an edge that fired mid-hold is skipped.

**Trade log columns:** `entry_time, entry_price, direction ("long"/"short"),
exit_time, exit_price, pips, exit_reason ∈ {sl, tp, opposite_signal, end_of_data}`.
`pips` = `(exit-entry)/PIP` long / `(entry-exit)/PIP` short — entry-at-ask /
exit-at-bid bakes the spread in.

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

### Trade log columns

`entry_time, entry_price, direction, exit_time, exit_price, pips, exit_reason`

`exit_reason ∈ {sl, tp, opposite_signal, end_of_data}`. An open position at end
of data is **force-closed**, never silently dropped.

### Out of scope for the engine

Position sizing (trades are tracked in **pips only**); multi-instrument support
(pip size `0.0001` is hardcoded for EURUSD).

---

## `lib/strategies.py` + `lib/signals.py` — strategies

The `Strategy` ABC lives in [`lib/engine.py`](#libenginepy--backtest-engine---strategy---engine)
(above). Concrete subclasses live here.

### `SmaCrossoverStrategy` ✅ — the reference / regression case

```python
from lib.strategies import SmaCrossoverStrategy

strat = SmaCrossoverStrategy(fast_n=20, slow_n=50, sl_pips=10, tp_pips=20, timeframe="5m")
trades = engine.backtest(strat)
```

- Keyword-only args. `fast_n`/`slow_n`/`timeframe` default; **`sl_pips`/`tp_pips`
  are required** — no default until the regression pins the prototype's values.
- `__init__` → `super().__init__(sl_pips, tp_pips, timeframe)` (which validates
  those), then requires `1 <= fast_n < slow_n` (`ValueError`).
- `exit_on_opposite_signal` stays `True` (inherited); **`reverse_on_opposite_signal
  = True`** — the prototype was always in the market, flipping long↔short on each
  opposite cross (§6).
- `generate_signals` — **mid price for signals only** (§0.3):
  `mid_close = (bid_close + ask_close) / 2`; `sma_fast`/`sma_slow` =
  `sma(mid_close, n)`; `long_signal`/`short_signal` = `crossover(sma_fast,
  sma_slow)`. Returns `df` + `mid_close, sma_fast, sma_slow, long_signal,
  short_signal` (§4 — intermediates kept for debugging/viz). Pure.
- No time arithmetic — §2.2's "bar t's close" rule is vacuous here (SMA/crossover
  are position-based). It matters for the future 4H-trend-filter strategy.

### `signals.py` — composable helpers

Pure **polars-expression** helpers `generate_signals()` calls into — they add no
columns and mutate nothing; the caller wires them up with `with_columns`.

```python
from lib.signals import sma, crossover

fast, slow = sma(pl.col("bid_close"), 20), sma(pl.col("bid_close"), 50)
cross_up, cross_down = crossover(fast, slow)     # two genuine pl.Boolean exprs
df = df.with_columns(long_signal=cross_up, short_signal=cross_down)
```

- **`sma(values, n)`** ✅ → `values.rolling_mean(n, min_samples=n)`. The first
  `n-1` outputs are **null**, never a partial average.
- **`crossover(fast, slow)`** ✅ → `(cross_up, cross_down)`. `cross_up` = `fast`
  was `<= slow`, now `> slow`; `cross_down` the reverse. Real `pl.Boolean`, no
  nulls. Warmup is handled by shifting the raw `fast - slow` diff — the first
  bar both SMAs are valid, `diff.shift(1)` is null, so `&` is null and
  `fill_null(False)` clears it: **no spurious crossover at the warmup boundary**.
  This is the spec §0.4 / §6 function — the result never degrades to object-dtype
  Python bools (the trap where a later `~` does a bitwise invert).

📋 later, with the strategies that need them: 4H `trend_filter` (lookahead-safe
`merge_asof`), DST-aware `session_flag`.

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
- **`test_engine.py`** ✅ (47 tests) — **Strategy**: abstract; ctor storage +
  validation; `exit_on_opposite_signal` default/override; `reverse` requires
  `exit_on_opposite_signal`. **`_resolve_exit` / `_sl_tp_levels`** (11):
  njit-compiled; long/short SL/TP, no-touch, same-bar-straddle → SL wins,
  `start_idx` hides earlier touches, the `PIP` offset. **Engine `__init__` /
  entries**: validates `base_1s`, rejects bad `signal_df`; `backtest` rejects
  non-Boolean and ambiguous signals; long → t+1 `ask_open`, short → `bid_open`,
  last-bar signal → no entry, entry strictly after the signal bar. **Exits**:
  long/short SL/TP/end-of-data on the 1s path (`pips ≈ ±pips`, `exit_time` =
  touch second, EOD `pips ≈ −2`); opposite-signal exit when SL/TP never fires;
  SL on an earlier bar preempts it; an SL that only prints on the signal-exit
  bar does **not** (§0.2); last-bar opposite edge falls through;
  `exit_on_opposite_signal=False` ignores it; rising-edge dedup; a re-cross
  mid-hold opens no second trade. **Reversal** (5): opposite-signal exit re-opens
  the other way at the same open (`entry_time`/`entry_price` == prev exit);
  chains long→short→long while opposite edges keep firing (each `entry_time` ==
  prev `exit_time`); the chain stops when a trade hits SL; `reverse` off is
  byte-identical to before (one trade then jump).
- **`test_signals.py`** ✅ (8 tests) — `sma` hand-checked values + null (not
  partial) warmup, rejects `n < 1`, pure; `crossover` on a zigzag flags the exact
  known up/down bar indices, output is `pl.Boolean` with no nulls, is pure, and
  fires no crossover at the SMA warmup boundary; **§0.4 / §6 regression** —
  result is real `pl.Boolean`, `sum()` is the small hand-known count (not
  inflated), and `~` is logical not (`sum(~x) + sum(x) == len`).
- **`test_strategies.py`** ✅ (13 tests) — constructor stores `fast_n`/`slow_n`
  and `sl_pips`/`tp_pips`/`timeframe` (via `super()`), rejects `fast_n >= slow_n`
  / `fast_n < 1` / `sl_pips=0`; `reverse_on_opposite_signal is True`;
  `generate_signals` output has `mid_close`/`sma_fast`/`sma_slow` + `pl.Boolean`
  signals with no nulls, is pure; **signals use mid, not bid/ask** (a spread-spike
  frame where the mid crosses on a different bar than the bid); no signal during
  the `slow_n` warmup; a hand-built one-crossover frame → `long_signal` True on
  exactly the expected bar; integration smoke through `Engine.backtest`.
- **`test_regression.py`** ✅ (6 tests, `-m slow`, skipped if the data file is
  absent) — end to end: `load_1s_data` → `resample("5m")` →
  `SmaCrossoverStrategy(20/50, sl 10 / tp 20)` → `Engine.backtest`. Asserts the
  §6 tolerances (trade count ±5% of 1,691, win rate ±3 pts of 33.0%, pips
  negative and `|pips|` in 0.5×–2× of 346.5), per-trade well-formedness (valid
  `direction`/`exit_reason`, `exit_time >= entry_time` with `==` ⇒ `sl`/`tp`,
  `entry_time` one bar after a crossover edge, `entry_price` == the bar's `ask`/
  `bid` open), no wall-clock overlap, and a headline-numbers lock.
- **Regression — result: PASS** (see [`regression.md`](regression.md)). Baseline
  **1,691 / −346.5 / 33.0%**; this build at `sl=10/tp=20` gives **1,714 / −453.1
  / 32.5%** (0 overlaps) — inside every §6 tolerance. Trade count matches at
  *any* SL/TP (1,700–1,733 across a 25-cell sweep) because it's set by the
  crossover count. The pip total at the arbitrary `10/20` runs 1.3× baseline;
  the notebook shows (a) a fitted cell — `mid, sl≈8/tp≈15` — reproduces −346
  within 1%, (b) the "assume SL first" fill difference is falsified (0 TP→SL
  flips), so the gap is a parameter mismatch (the spec never recorded the
  prototype's SL/TP), not an engine bug. Full analysis + SL/TP sweep grid +
  pip-gap decomposition in [`notebooks/regression.ipynb`](notebooks/regression.ipynb).
- **`resample()` lookahead tests:** ✅ in `test_data.py` — (a) trailing partial
  bucket dropped when the data doesn't end on a boundary, kept when it does;
  (b) for 5m and 1h, `close_time == bucket_start + timeframe`, not a hardcoded
  duration; (c) bid/ask OHLC aggregation checked on a few hand-verifiable rows.
