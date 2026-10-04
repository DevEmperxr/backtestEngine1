# FX Backtester — Usage

Companion to [`fx_backtester_spec.md`](fx_backtester_spec.md). The spec says *why*
each decision was made; this doc shows *how* to use each component once it exists.

**Status legend:** ✅ built · 🚧 in progress · 📋 planned (API from the spec, may
still shift) · ⏸️ deferred (not this build)

| Module | Purpose | Status |
|---|---|---|
| `lib/data.py` | Load + sanity-check 1s data, resample to coarser timeframes | ✅ |
| `lib/engine.py` | `Strategy` ABC · `Engine` (`backtest` + `evaluate`) · `_resolve_exit` 1s SL/TP walk | ✅ |
| `lib/strategies.py` | Concrete `Strategy` subclasses | ✅ `SmaCrossoverStrategy` |
| `lib/signals.py` | Pure, composable signal helpers strategies call into | ✅ `sma`, `crossover` · 📋 trend filter, session flag |
| `lib/evaluate.py` | Normal + adversarial metrics, plots | ✅ `evaluate` · `adversarial` · `bootstrap_ci` · `mc_drawdown` · `plot_*` |
| `fx_viz/` | Live in-notebook chart (`FxChart`) + `Strategy.visualize()` | ✅ |

---

## Setup

```bash
# from repo root
python -m venv .venv
.venv\Scripts\activate            # Windows

pip install polars numba numpy matplotlib

# only needed for fx_viz (lazy-imported -- headless backtests/tests never pay for this)
pip install python-lightweight-charts pyarrow pandas playwright
playwright install chromium   # only if you want to verify chart rendering yourself, not for normal use
```

- **polars** — the entire data layer (no pandas at the data layer).
- **numba** — JITs the inner 1-second fill-resolution loop in the engine.
- **matplotlib** — evaluation charts (equity curve, monthly P&L, MC distributions).
- **python-lightweight-charts** — `fx_viz`'s chart engine (`StreamChart`). Pulls in
  `fastapi`/`uvicorn`/`websockets`.
- **pyarrow**, **pandas** — `fx_viz` hands the chart library pandas, not polars;
  `polars.to_pandas()` needs `pyarrow`.
- **playwright** — only if you want to drive a headless browser against `fx_viz`
  yourself (screenshots, simulated clicks/pans) the way this module's hands-on
  verification was done; not a runtime dependency of anything in `lib/` or
  `fx_viz/`.

Data files live in `data/` (git-ignored). The 1s EURUSD file is a single CSV with
bid and ask OHLCV side by side:

```
timestamp, bid_open, bid_high, bid_low, bid_close, bid_volume,
           ask_open, ask_high, ask_low, ask_close, ask_volume
```

`timestamp` is an ISO string with a UTC offset (`2024-01-01 22:00:12+00:00`).

---

## `lib/data.py` — data layer ✅

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

## `lib/engine.py` — backtest engine ✅

### `Strategy` (ABC) ✅

The formal strategy interface (spec §2.2). A concrete strategy subclasses it,
calls `super().__init__(sl_pips, tp_pips, timeframe)`, then adds its own params.

```python
from abc import ABC, abstractmethod
import polars as pl

class Strategy(ABC):
    exit_on_opposite_signal: bool = True     # also close on the opposite signal (on top of SL/TP)
    reverse_on_opposite_signal: bool = False  # ...and immediately re-open the other way

    # chart-rendering metadata (visualizer spec §2) -- see "fx_viz" below
    line_columns: list[str] = []
    marker_columns: list[str] = []
    region_columns: list[str] = []

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

    def visualize(self, engine: "Engine", chart=None, show_trades: bool = False, **kw):
        """Chart this strategy -- see "fx_viz" below for the full contract."""
```

| member | kind | notes |
|---|---|---|
| `sl_pips`, `tp_pips` | instance (ctor) | pip distances, must be `> 0` |
| `timeframe` | instance (ctor) | `"5m"`, `"1h"`, … — drives the "bar t's close" math |
| `exit_on_opposite_signal` | class attr, default `True` | engine also closes on the opposite signal, on top of SL/TP |
| `reverse_on_opposite_signal` | class attr, default `False` | on an opposite-signal exit, re-open the other way at the same open ("always in the market"); requires `exit_on_opposite_signal` |
| `line_columns`/`marker_columns`/`region_columns` | class attr, default `[]` | which `generate_signals()` columns `visualize()` plots — see **fx_viz** below |
| `generate_signals(df)` | abstract | the one thing a subclass must implement |
| `visualize(engine, chart=None, show_trades=False, **kw)` | concrete | charting entry point — see **fx_viz** below |

`Strategy(...)` directly raises `TypeError` (abstract). SL/TP/timeframe are
constructor params because they *define* a strategy variant — not engine-run args.

### `Engine` ✅

```python
from lib.engine import Engine

engine = Engine(signal_df, base_1s)    # resampled bars + the 1s base
trades = engine.backtest(strategy)     # -> pl.DataFrame trade log
# metrics = evaluate(trades, ...)      # lib.evaluate — §3.1 done, §3.2 planned
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
exit_time, exit_price, pips, exit_reason ∈ {sl, tp, opposite_signal, end_of_data},
spread_pips_paid`.
`pips` = `(exit-entry)/PIP` long / `(entry-exit)/PIP` short — entry-at-ask /
exit-at-bid bakes the spread in. `spread_pips_paid` = half-spread at the entry
open + half-spread at the exit instant (1s bar close for sl/tp/eod, signal bar
for opposite_signal), in pips — so **gross P&L = net `pips` + `spread_pips_paid`**
(used by `evaluate.adversarial`).

### `Engine.evaluate(trades, *, starting_balance=10_000, pip_value=1.0, seed=None, **kw)` ✅

Thin delegator (spec §2.1) — runs `evaluate` + `adversarial` + `bootstrap_ci` +
`mc_drawdown` and merges:

```python
{"summary", "equity_curve", "monthly",              # evaluate() §3.1
 "adversarial": {"gross_vs_net", "ex_best_month", "ex_best_trades",
                 "sample_size", "bootstrap_ci", "mc_drawdown"},
 "verdict"}                                          # sample-size-gated, top level
```

`seed` reaches the two resampling calls; extra kwargs (`exclude_best_pct`,
`min_trades`, `n_resamples`, `n_shuffles`, `confidence`) route to whichever
function takes them.

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

`exit_reason ∈ {sl, tp, opposite_signal, end_of_data}` plus `spread_pips_paid`.
An open position at end of data is **force-closed**, never silently dropped.

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

## `lib/evaluate.py` — evaluation ✅ §3.1 + §3.2

### `evaluate(trades, *, starting_balance=10_000.0, pip_value=1.0) -> dict` ✅

Normal metrics (§3.1). `pip_value` = dollars of P&L per pip — fixed position
size, an evaluate-time input only (§2.4). `rf = 0` everywhere (Sharpe/Sortino
are raw return/risk ratios). Wiring into `Engine.evaluate` is a trivial
follow-up.

```python
from lib.evaluate import evaluate
r = evaluate(trades, starting_balance=10_000, pip_value=1.0)
r["summary"]        # dict of scalars
r["equity_curve"]   # pl.DataFrame: exit_time, cum_pips, equity, drawdown_pct  (one row / trade)
r["monthly"]        # pl.DataFrame: month (date), pips, pnl, n_trades, win_rate
```

**`summary` scalars:** `n_trades`, `win_rate` (%), `expectancy_pips`,
`profit_factor` (gross win / |gross loss| pips; `inf` if no losers, `None` if no
trades), `avg_win_pips`, `avg_loss_pips` (`None` if none), `total_pips`,
`total_return_pct`, `max_drawdown_pct` (**signed, negative** — % below the
high-water mark, which starts at `starting_balance`), `max_drawdown_date` (exit
timestamp of the trough, `None` if never underwater), `sharpe`, `sortino`
(annualized ×√252 from daily returns = daily P&L / `starting_balance`, bucketed
by `exit_time` date over days that traded; ddof=1; `None` when std is undefined
or 0 — e.g. a single trading day), `mar` (`CAGR / |max_dd_fraction|`; CAGR over
`entry.min()→exit.max()` in 365.25-day years).

- **Win** iff `pips > 0`, **loss** iff `pips < 0`; an exact break-even counts in
  `n_trades` only.
- **Empty frame** → zeros/`None`, no crash; the two frames come back empty with
  their schemas.

### `adversarial(trades, *, starting_balance=10_000, pip_value=1.0, exclude_best_pct=(0.01, 0.05), min_trades=100) -> dict` ✅

The deterministic §3.2 checks (`bootstrap_ci` + `mc_drawdown` are the resampling
part, below). Needs the `spread_pips_paid` column (`ValueError` otherwise).
Returns:

| key | contents |
|---|---|
| `gross_vs_net` | `net_pips`, `spread_paid_pips`, `gross_pips` (= net + spread), the `_pnl` versions, and `edge_assessment` — one of *"no edge — gross P&L not positive"*, *"edge existed, costs ate it"*, *"profitable after costs"* |
| `ex_best_month` | totals with the single best-by-pips calendar month removed: `dropped_month`, `dropped_month_pips`, `pips`, `pnl`, `full_pips` |
| `ex_best_trades` | list, one per `exclude_best_pct`: `{pct, n_dropped = ceil(n·pct), pips, pnl}` after dropping the top-pips trades |
| `sample_size` | `{n_trades, min_trades, low_sample, warning}` |
| `verdict` | `"profitable"` / `"unprofitable"` — **gated**: below `min_trades` it reads `"inconclusive (N trades, need ≥100)"` instead |

Real 2024 run (SMA 20/50, sl 10/tp 20): net **−453** pips, spread paid **598**,
gross **+145** → *"edge existed, costs ate it"* (though +145 over 1,714 trades is
barely an edge). Dropping the best month (Nov, +291) → −744. Verdict:
*unprofitable*.

### `bootstrap_ci(trades, *, n_resamples=10_000, confidence=0.95, seed=None) -> dict` ✅

Percentile bootstrap (resample the `pips` array **with replacement**), not a
normal approximation — robust to the skewed / fat-tailed trade P&L. Deterministic
given `seed`. Returns, for `win_rate` (%) and `expectancy_pips` each:
`{observed, mean, ci_low, ci_high}` (the `(1−confidence)/2` and `1−…` percentiles).

Real 2024 run, seed-fixed: expectancy observed −0.26 pips/trade, 95% CI
**[−0.73, +0.22]** — straddles zero, i.e. no statistically distinguishable edge.

### `mc_drawdown(trades, *, n_shuffles=10_000, starting_balance=10_000.0, pip_value=1.0, seed=None) -> dict` ✅

Shuffles the **order** of the realized pips `n_shuffles` times (values, and so
total P&L, unchanged — only the equity path) and rebuilds the max drawdown each
time. Deterministic given `seed`; the distribution depends only on the multiset
of pips, not their input order.

- `observed_max_drawdown_pct` — the real historical ordering
- `median`, `p95` (5th percentile of the signed DDs — the worse tail), `worst` (min)
- `percentile_rank` — % of reorderings worse than reality
- `fragile` (bool) — `observed` milder than the shuffled distribution's 25th
  percentile (a large fraction of reorderings would have been worse → the
  reported DD may be a lucky-ordering artifact) — `fragile_note` explains it
- `note` — the §3.2 scope caveat, verbatim: *sequence risk on the trades you
  already have; it cannot detect a missing edge, and a good shuffle distribution
  is not validation of the strategy*

Real 2024 run, seed-fixed: observed −8.9%, shuffled median −6.8%, worst −12.4%,
`percentile_rank` ~6% → **not fragile** (the real ordering was, if anything, a
touch unlucky).

> The MC shuffle tests **sequence risk on the trades you already have** — it can't
> detect an edge that doesn't exist. A good shuffle distribution is not validation
> of the strategy.

### plots ✅ — `plot_equity(result)`, `plot_monthly(result)`, `plot_mc_drawdown(mc_result)`

Each returns a `matplotlib.figure.Figure` and **never** calls `.show()` /
`.savefig()` — the caller decides. `matplotlib` is **lazy-imported inside each
function**, so importing `lib.evaluate` (or running the test suite) never pulls
it in — same rule `fx_viz` follows for its own GUI deps. `plot_equity` = $ equity line + drawdown shaded
on a twin axis; `plot_monthly` = green/red monthly-P&L bars; `plot_mc_drawdown` =
histogram of `mc_drawdown()`'s `distribution` with the observed DD marked.

```python
from lib.evaluate import plot_equity
fig = plot_equity(report); fig.savefig("equity.png")   # caller's call
```

`notebooks/full_report.ipynb` runs the whole framework end-to-end and renders all three.

---

## `fx_viz` — visualizer ✅

Companion to [`fx_visualizer_widget_spec.md`](fx_visualizer_widget_spec.md), which
supersedes `fx_backtester_spec.md`'s §5 placeholder. Live, in-notebook charting
built on [`python-lightweight-charts`](https://pypi.org/project/python-lightweight-charts/)'s
`StreamChart` (a local FastAPI/WebSocket server embedded as an iframe) — not raw
`anywidget`. The §1.1 validation spike that justified this choice, and every
gotcha below, were confirmed **hands-on** with a Playwright-driven headless
Chromium (`notebooks/viz_spike.ipynb`), not by reading the library's docs.

Two layers: `fx_viz.FxChart` (generic, declarative, knows nothing about
strategies) and `Strategy.visualize()` (the integration glue — knows about
`Engine`/trades, calls into `FxChart`).

### Quick start

```python
# CELL 1 -- once per session
from lib.data import load_1s_data, resample
from lib.engine import Engine
from lib.strategies import SmaCrossoverStrategy

raw    = load_1s_data("data/EURUSD_1s_2024.csv")
engine = Engine(resample(raw, "5m"), raw)

class VizStrategy(SmaCrossoverStrategy):
    line_columns   = ["sma_fast", "sma_slow"]
    marker_columns = ["long_signal", "short_signal"]

strategy = VizStrategy(fast_n=20, slow_n=50, sl_pips=10, tp_pips=20)
chart = strategy.visualize(engine, show_trades=True)
chart   # displays the iframe
```

```python
# CELL 2 -- rerun whenever the strategy changes; SAME chart, viewport persists
strategy.visualize(engine, chart=chart, show_trades=True)
```

`notebooks/viz_demo.ipynb` is this exact pattern, ready to run.

### `FxChart` ✅ (`fx_viz/chart.py`)

```python
from fx_viz import FxChart

chart = FxChart(width=820, height=460, port=8765)   # starts a local StreamChart server
chart.plot(df, spec=[
    {"kind": "candle", "column": "bid"},                              # -> bid_open/high/low/close
    {"kind": "line", "column": "sma_fast", "color": "#E8A33D"},
    {"kind": "marker", "column": "long_signal", "shape": "arrow_up"},
    {"kind": "region", "column": "session"},                          # full-height background band
    {"kind": "region", "column": "zone",                              # bounded box instead
     "top_column": "zone_top", "bottom_column": "zone_bottom"},
])
```

**Column contract** (`spec` entries, every `kind` takes an optional `"pane"` int,
default `0` = main price pane):

| `kind` | needs | notes |
|---|---|---|
| `"candle"` | `open`/`high`/`low`/`close`, or `"column": "bid"` → `bid_open`/… | at most one per chart (it *is* the chart's own series) |
| `"line"` | `"column"` (numeric) | `null` runs are **not** a gap by default in the underlying library (see gotchas) — `FxChart` works around this by splitting a column into one line series per contiguous non-null run, so a bounded/hline-style column (null outside, constant inside) renders correctly without you doing anything |
| `"marker"` | `"column"` (boolean) | `True` rows get a glyph; `shape` (`circle`/`arrow_up`/`arrow_down`/`square`), `color`, `position` (`above`/`below`/`inside`) |
| `"region"` | `"column"` (boolean) | contiguous `True` runs shaded. Add `top_column`/`bottom_column` (numeric, constant per run) for a bounded box instead of full-height shading |

Calling `.plot()` again is **idempotent**: matching columns update their
existing series (`.set()`) instead of recreating them, so zoom/pan/timeframe
survive a rerun; columns no longer in `spec` get `.delete()`d.

Other `FxChart` methods, all used internally by `Strategy.visualize()` but
public if you're building something custom:

- **`on_range_change(callback)`** — `callback(bars_before, bars_after)` on every
  pan/zoom (small/negative ⇒ near that edge of the loaded window). This is the
  spec §5 lazy-load hook.
- **`add_timeframe_switcher(options, default, callback)`** — the native topbar
  selector; `callback(new_timeframe)` on click. **Call this exactly once** per
  chart — see gotchas.
- **`position_tool(entry, stop, target, entry_time, end_time=None, ...)`** —
  the long/short risk-reward box (red stop zone, green target zone). One call
  per trade; no `spec`/column entry for this (one object per trade doesn't fit
  the per-bar column shape). See gotchas for the bar-alignment requirement.
- **`batch()`** — internal; combines several script sends into one atomic send.
  Don't wrap a `.plot()` call in it yourself (see gotchas).

### `Strategy.visualize(engine, chart=None, show_trades=False, *, initial_bars=500, warmup_bars=200, fetch_chunk=500, edge_margin=50, timeframes=(...)) -> FxChart` ✅

The primary interface — real work happens through a `Strategy` subclass, not
raw `FxChart` calls.

- **Spec is auto-built**, never hand-written: a candle (`bid_*`) entry, plus one
  `"line"`/`"marker"`/`"region"` entry per name in `line_columns`/
  `marker_columns`/`region_columns` (§2), each with its own color from a small
  palette (lines and markers get *disjoint* palette ranges, so e.g. 2 lines +
  2 markers are 4 genuinely distinct colors, not 2 colors used twice). An
  undeclared column is simply never plotted — explicit wins, no guessing.
- **Lazy-loading (§5):** only the last `initial_bars` bars load at first.
  Panning within `edge_margin` bars of the loaded window's edge fetches another
  `fetch_chunk` bars on that side (`on_range_change`). `engine.base_1s` is
  re-resampled to the active timeframe **once** and cached — an ordinary pan
  only re-slices the cached frame, never re-resamples.
- **Timeframe-switching (§4) is display-only.** Clicking a topbar button
  resamples `engine.base_1s` fresh and recomputes `generate_signals()` *for
  display* — the SMA lines/markers you see genuinely change. It does **not**
  re-run `engine.backtest()` and does **not** change `self.timeframe` on the
  strategy (deliberately — re-backtesting, including the numba 1s walk, on
  every click would make the chart sluggish, §8.5's same reasoning). The
  practical consequence: `show_trades=True`'s position-tool boxes always
  reflect the real backtest at the strategy's *actual* configured timeframe,
  so they generally won't line up with a crossover you're looking at on some
  *other* timeframe — that's not a bug, it's two different things being shown
  together.
- **No-lookahead discipline**, the thing to trust most here: every window
  handed to `generate_signals()` is extended **strictly backward in time** by
  `warmup_bars` so indicators aren't null/seamed at the loaded edge, then those
  extra rows are dropped before anything is plotted or returned. Covered by
  dedicated tests (`TestWindowedSignalsNoLookahead`) that poison data on both
  sides of the window and confirm the output is unaffected either direction —
  not just "looks right once," structurally can't read data it wasn't given.
- **`show_trades=True`:** runs `engine.backtest(self)` **once** (not on every
  rerun/pan/switch — §8.5), then draws one `position_tool()` box per trade
  whose entry falls in the currently-loaded window, with `stop`/`target`
  recomputed from `entry_price` + `self.sl_pips`/`self.tp_pips` via the same
  `_sl_tp_levels` the engine itself used. Default `False` for the same reason
  as §8.5: the fast signal-iteration loop shouldn't pay for a backtest on
  every keystroke-driven rerun.

### Gotchas (confirmed hands-on, not from the library's docs)

These matter if you're extending `fx_viz`/`visualize()` — all already handled
transparently by the code above, listed here so a future change doesn't
silently reintroduce one:

- **tz-naive only.** Any timestamp reaching this library (a `time` column, a
  `PositionTool`'s `entry_time`/`end_time`) must be tz-naive — a tz-aware value
  throws `TypeError` inside the library's own `_format_time`. Check *every* new
  code path that hands it a timestamp, not just the first one found — this bit
  twice in the same module (the main plot path, then again at `position_tool`,
  which takes raw `datetime`s straight from the trade log rather than going
  through the same `_to_pandas()` prep).
- **`PositionTool` needs bar-aligned times.** A sub-bar-precision `entry_time`/
  `end_time` collapses the box to a near-zero-width sliver instead of spanning
  the real range — confirmed by direct reproduction. SL/TP exits resolve on
  the real 1s price path (§2.3) and so land on an exact second, never `:00` —
  i.e. this hits ~40% of real trades, not a rare edge case. Fixed by
  `_nearest_bar_at_or_before()` snapping both times to a real bar before they
  reach `position_tool()`.
- **`null` does not render as a gap by default.** Lightweight Charts v5's line
  series silently interpolates straight across null/whitespace points instead
  of breaking — confirmed with a sharp step-function test (a smooth/linear
  test signal can't tell the two apart, since a straight connecting line and a
  true gap look identical when the trend is already linear). `FxChart._plot_line`
  works around this by splitting a column into one `create_line()` series per
  contiguous non-null run.
- **A series' marker-plugin setup is asynchronous with no "ready" signal.**
  Touching a brand-new series' markers immediately can throw `Cannot read
  properties of undefined (reading 'setMarkers')` — and in Chromium, an
  uncaught exception mid-script aborts every *later* statement in that same
  combined send, which once silently prevented a topbar switcher batched right
  after it from ever appearing. `FxChart.plot()` applies marker *data* in a
  separate phase, after a real wall-clock gap for brand-new series, via a
  self-healing JS retry loop instead of the library's own `marker_list()`
  (which sends unconditionally and lets it throw).
- **No "replace a widget" API.** Re-registering `add_timeframe_switcher`/
  `on_range_change` on every `visualize()` rerun stacks a new topbar row on
  top of the old one instead of replacing it (confirmed: 3 duplicate rows
  after 3 reruns). `visualize()` wires both exactly once per `chart`
  (`chart._fx_events_wired`); a mutable state dict stored on the chart itself
  (`chart._fx_live`) is what lets a rerun with different strategy params still
  take effect without re-wiring.
- **`StreamChart` ships a CSP header with no `style-src`**, which blocks the
  inline-style mutations the JS uses to resize panes — breaks dynamic
  `add_pane()` silently (14 browser console errors, no Python exception).
  `FxChart` patches this at the HTTP-response level, process-wide, the first
  time an `FxChart` is created (can't be fixed by editing the installed
  package — a reinstall would wipe it).
- **`StreamChart`'s window (`StreamWindow`) is missing `_id_gen`**, a class
  attribute the desktop `Window` class has that `marker()`/`marker_list()`
  need. `FxChart` patches it in at construction time, same mechanism as the
  CSP fix.
- **Don't wrap a `.plot()` call in an outer `chart.batch()`.** `plot()` already
  does its own two-phase send internally for marker timing (see above);
  `batch()` is reentrant, so an outer wrapper makes the inner call join that
  one send and silently defeats the two-phase split.
- **A box/region positioned outside the current viewport can look "missing."**
  `StreamChart` doesn't auto-fit to the full loaded range — it shows a
  scrolled view of the most recent portion. A region on older data is still
  correctly positioned; pan to it (or, for a one-off check,
  `chart._sc.run_script(f"{chart._sc.id}.chart.timeScale().fitContent()")` to
  force the whole loaded range into view) to confirm.
- **Playwright's `page.screenshot()` (CDP capture) can itself trigger a
  one-off `setMarkers` console error** via some forced-repaint path unrelated
  to normal rendering — confirmed via A/B test (0 errors polled 10s without a
  screenshot call; 1 appears specifically right after one). A testing-harness
  artifact, not something real browser/notebook usage triggers — don't chase
  it if you see it while testing this way yourself.

### Verification method

Nothing above was confirmed by reading the library's source alone — every
claim was reproduced hands-on with Playwright driving a real headless
Chromium against the actual served page: real mouse drags for pan events,
real clicks for the topbar switcher, WebSocket frame sniffing to confirm what
data actually reached the browser, and screenshots read back directly. See
`notebooks/viz_spike.ipynb` (the original §1.1 spike) for the technique if you
need to verify a future change the same way — it's cheap to redo and catches
things a "did it throw?" check alone would miss (several of the gotchas above
rendered silently wrong with zero exceptions anywhere).

---

## End-to-end

```python
from lib.data import load_1s_data, resample
from lib.engine import Engine
from lib.strategies import SmaCrossoverStrategy
from lib.evaluate import plot_equity, plot_monthly, plot_mc_drawdown

df      = load_1s_data("data/EURUSD_1s_2024.csv")
engine  = Engine(resample(df, "5m"), df)

trades  = engine.backtest(
    SmaCrossoverStrategy(fast_n=20, slow_n=50, sl_pips=10, tp_pips=20)
)
report  = engine.evaluate(trades, starting_balance=10_000, pip_value=1.0, seed=0)

print(report["verdict"])               # sample-size-gated
print(report["summary"])               # §3.1 scalars
report["adversarial"]["gross_vs_net"]  # §3.2: is the edge real / did costs eat it
report["adversarial"]["bootstrap_ci"]  # CI on win rate & expectancy
report["adversarial"]["mc_drawdown"]   # drawdown vs shuffled orderings

fig = plot_equity(report)              # -> matplotlib Figure (caller shows/saves)
```

---

## Testing (spec §6)

**157 tests** — `pytest lib/tests/` (151 fast; 6 more with `-m slow` when the
2024 data file is present).

```bash
pytest lib/tests/            # fast suite
pytest lib/tests/ -m slow    # + the end-to-end regression
```

- **`test_data.py`** ✅ (27 tests) — synthetic-frame tests for every hard check
  (clean data passes; conflicting duplicate timestamp / broken OHLC / negative
  spread / null / NaN / missing column each raise), the gap classifier (weekend
  size guard, holiday, fabricated mid-week hole), the per-year holiday calendar
  (Easter computus, auto-derived from data span for an arbitrary year), a
  sub-threshold hole still shows in the report, and `resample` (bid+ask OHLC on
  hand-checked rows, trailing-partial-bucket drop/keep, `close_time` per
  timeframe, flat-candle gap fill, weekend gap left unfilled).
- **`test_engine.py`** ✅ (49 tests) — **Strategy**: abstract; ctor storage +
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
  byte-identical to before (one trade then jump). **`spread_pips_paid`** (2):
  flat market → full spread == `−pips` (gross 0); a wider spread on the exit
  second is what's recorded.
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
- **`test_evaluate.py`** ✅ (38 tests) — **§3.1** (13): win rate / expectancy /
  profit factor / avg win-loss (4×+20, 6×−10); `pip_value` scales the \$ metrics
  only; exact peak→trough drawdown % and date; monotone equity → 0 DD / `None`
  date; equity-curve columns + cumulative values; monthly sums across 3 months;
  Sharpe **and** Sortino vs hand-computed `mean/std·√252`; single trading day →
  `None`; empty frame → zeros/`None` + schema'd empties; all-wins → `inf`;
  all-losses → `0.0`; break-even counts in neither rate; MAR ==
  `CAGR / |max_dd_fraction|`. **§3.2 adversarial** (10): gross-vs-net shows
  "costs ate the edge" (net −2 / gross +10) and "no edge" (gross −12); `gross ==
  net + spread` always; missing `spread_pips_paid` → `ValueError`; drop-best-month
  changes the total by exactly that month; drop-best-N% removes `ceil(n·pct)`
  trades (kills the outlier); the verdict is **withheld** below `min_trades` even
  when net is positive, and real above; empty → no crash. **§3.2 resampling**
  (11): `bootstrap_ci` — seed-deterministic, different seed differs, CI brackets
  observed and mean, degenerate (all-equal pips) collapses to the point, matches
  a direct numpy computation, empty → no crash; `mc_drawdown` — seed-
  deterministic, distribution depends only on the pip *multiset* not input order
  (only `observed` differs), "all losses first" → near-worst + not fragile,
  interleaved-with-clustering-risk → fragile + most reorderings worse, small n
  and empty → no crash. **Orchestration + plots** (4): `Engine.evaluate` merges
  all sections + gates the verdict + is seed-reproducible; the 3 `plot_*`
  functions return a `matplotlib.figure.Figure` (Agg backend, `plt.close` after)
  and don't crash on an empty result.
- **`test_regression.py`** ✅ (6 tests, `-m slow`, skipped if the data file is
  absent) — end to end: `load_1s_data` → `resample("5m")` →
  `SmaCrossoverStrategy(20/50, sl 10 / tp 20)` → `Engine.backtest`. Locks the
  headline numbers (`1,714 / −453.1 / 32.5%` + exit mix) as the regression
  tripwire; loose stability bands (count 1,500–2,000, win 25–40%, edge negative);
  per-trade well-formedness (valid `direction`/`exit_reason`, `exit_time >=
  entry_time` with `==` ⇒ `sl`/`tp`, `entry_time` one bar after a crossover edge,
  `entry_price` == the bar's `ask`/`bid` open); no wall-clock overlap.
- **Regression — result: PASS** (see [`regression.md`](regression.md)). Locked
  baseline on the 1s data at `sl=10/tp=20`: **1,714 trades / −453.1 pips / 32.5%
  win**, 0 overlaps. The spec's old **1,691 / −346.5 / 33.0%** figure is
  **retired** — a direct bar-level diff confirmed the prototype's 5-min pull was
  *incomplete* (29 bars the 1s data has that the 5-min data lacks, 0 the other
  way, clustered at low-liquidity periods — Christmas, July 4th, the Nov 21
  sell-off). The difference is source-data completeness, **not** an engine /
  `resample` / fill bug. Trade count is invariant to SL/TP (1,700–1,733 across a
  25-cell sweep) — it's set by the crossover count, which is the real proof the
  signal/entry/reversal logic is correct. Full analysis + confirming loop in
  [`regression.md`](regression.md) / [`notebooks/regression.ipynb`](notebooks/regression.ipynb).
- **`resample()` lookahead tests:** ✅ in `test_data.py` — (a) trailing partial
  bucket dropped when the data doesn't end on a boundary, kept when it does;
  (b) for 5m and 1h, `close_time == bucket_start + timeframe`, not a hardcoded
  duration; (c) bid/ask OHLC aggregation checked on a few hand-verifiable rows.
- **`test_viz.py`** ✅ (16 tests) — `fx_viz`'s pure-logic pieces only; anything
  needing a live browser (candle/line/marker/region rendering, hot-reload, pane
  add/delete) was verified by hand instead, see **fx_viz**'s gotchas/
  verification-method sections above, not re-covered here. `_contiguous_runs`
  (6): single/empty/bounded/leading-trailing/single-bar runs — the gap-
  segmentation helper behind the null-doesn't-gap-by-default workaround.
  `_to_pandas` (2): strips tz, passes tz-naive through unchanged. **
  `TestWindowedSignalsNoLookahead`** (6, the most load-bearing ones here): a
  windowed-with-warmup computation matches a full-dataset computation exactly,
  bar for bar; degrades safely (more nulls, never a wrong or fabricated value)
  when `warmup_bars` is less than an indicator's own lookback; the zero-offset
  edge case needs no clamp; and the two most direct lookahead checks —
  poisoning data at/after `end_idx` or before `compute_start` and confirming
  the result is provably unaffected either direction, not just "looks right
  once." `TestTradesInWindow` (3) — the trade-window filter behind the
  `PositionTool` overlay: keeps only entries within range, boundary-inclusive,
  empty trade log → empty result.
