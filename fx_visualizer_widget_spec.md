# FX Signal Visualizer — Jupyter Chart Build Spec

**Status**: revised after workflow correction — this replaces the first draft
of this document, not just an addendum. The first draft under-scoped the
problem (treated pan/zoom/multi-pane/timeframe-switching/lazy-load as
out-of-scope caller responsibilities). They are not — they're core to the
actual workflow and are specified below.

**Relationship to `fx_backtester_spec.md`**: still supersedes that document's
§5, for the same reason as before (this needs to be a live in-notebook tool,
not a standalone app) — that part of the original reasoning didn't change.

**Important scope note**: `fx_backtester_spec.md` describes exactly what
Claude Code already built and validated (per its status report) — it should
not be edited to describe work that hasn't happened yet, to avoid confusing
future work on that codebase about what actually exists. Everything in this
document, including the required changes to the existing `Strategy` class,
lives here instead. §2 below is a **precise, additive patch spec** for
`lib/engine.py`'s `Strategy` ABC — read it as "add exactly this," not as a
description of what's already there.


---

## 0. The workflow being built, stated precisely

1. Open a notebook, load chart data.
2. Call the chart visualizer.
3. Write indicators/signals into the data.
4. Reload/rerun the code → the chart updates.
5. Zoom / pan / drag the chart.
6. Separate some indicators into their own charting sub-window (pane).
7. Switch timeframes.
8. Lazy-load data, so charts stay fast regardless of dataset size.

Items 1–4 are what the first draft handled (a Python-driven, declarative,
column-generic `.plot(df, spec)` call that updates an already-displayed
widget). Items 5–8 require something the first draft explicitly didn't
build: **the chart itself needs to be able to ask for more/different data**
— on pan near a loaded edge, on a timeframe click, on opening a new pane.
That's a request/response relationship, not a one-way push. This is the
actual architectural gap in the first draft, not a missing feature to bolt
on top of the old design.

---

## 1. Foundation: build on `python-lightweight-charts`, not raw `anywidget`

**Revised decision.** The first draft proposed hand-building a custom
`anywidget` widget wrapping a vendored copy of the raw JS library — reasonable
if native pan/zoom/panes/timeframe-switching had to be built from scratch,
but they don't need to be:

- **`python-lightweight-charts`** (PyPI, a maintained fork bringing
  `louisnw01/lightweight-charts-python` up to Lightweight Charts v5) already
  provides: native pan/zoom/crosshair (free, from the underlying v5 JS lib —
  item 5), a full pane-management API (`add_pane`, `move_pane`, `resize_pane`,
  `remove_pane` — item 6), built-in timeframe-selector events (item 7), and
  live-update methods (`chart.set(df)`, `chart.update(series)`,
  `chart.marker(...)`) designed to be called repeatedly with new data — which
  is structurally already the "call again from a rerun cell" pattern items
  3/4 need. It explicitly lists Jupyter Notebooks as a supported environment,
  separate from its desktop-window (pywebview) mode.

Using this as the engine means not reinventing panes, native chart
interaction, or timeframe-switching plumbing — all real, fiddly work that a
maintained library has already solved. What's still genuinely custom to this
project, and what this spec actually needs to design, is narrower:

1. A **generic, declarative `.plot(df, spec)` layer** on top of this
   library's more manual/imperative API (`chart.set()`, `chart.marker()`,
   per-series calls) — reading arbitrary dataframe columns by name, same
   "point at a column, it draws" contract as the first draft, still not
   provided by the underlying library itself.
2. **Hot-reload wiring validated against the exact two-cell workflow**
   (§2 below) — the library supports live updates in principle, but the
   specific "create once in cell A, mutate from cell B on every rerun,
   preserve viewport" pattern needs to be built and tested explicitly, not
   assumed to fall out for free.
3. **Lazy-loading against this project's own data** (§4) — inherently
   specific to our pipeline (resampling from 1s base data), not something any
   generic charting library provides out of the box.

### 1.1 Required first step: a validation spike, not a leap of faith

Before committing further design on top of this library, actually verify
hands-on (since this can't be confirmed by reading docs alone):
- Does its Jupyter Notebook integration genuinely support **live updates to
  an already-rendered notebook cell output** (matching item 4), or does it
  only render a fresh static/interactive snapshot per cell execution? Its
  separate "StreamChart" feature (serves a chart over HTTP/WebSocket, viewable
  in any browser) suggests live-update is a real, designed-for capability —
  but confirm the *specific* Jupyter-embedded case, not just the
  StreamChart-in-a-browser-tab case, actually behaves the way item 4 needs.
- Does `add_pane` expose a way to route a specific dataframe column to a
  specific pane cleanly, and can panes be added/removed dynamically as `spec`
  changes between calls (item 6), or only configured at chart-creation time?
- Does the pane/timeframe API expose an event hook for "visible range changed"
  / "user requested a different timeframe" that Python code can subscribe to
  — required for lazy-loading (§4) and for timeframe-switching (§3) to
  actually fetch new data rather than just resizing what's already loaded.

**If this spike finds the library's Jupyter live-update model doesn't fit**
(e.g. it only supports StreamChart-in-a-separate-browser-tab, not
in-notebook-cell live updates), fall back to the original `anywidget` +
vendored-JS plan from the first draft — now knowing panes are natively
available in the raw v5 JS library too (§1 confirmed this), so a from-scratch
build would no longer need to hand-roll multi-pane support either. Either
path, panes/pan/zoom/timeframe-switching are now known to be available
natively in the underlying v5 JS engine — the open question is only which
Python delivery layer actually gets it working live inside a notebook cell,
and that's exactly what the spike is for.

---

## 2. Required patch to the existing `Strategy` class (`lib/engine.py`)

**Not yet built.** The `Strategy` ABC as Claude Code delivered it has
`sl_pips`, `tp_pips`, `exit_on_opposite_signal`, and the abstract
`generate_signals(self, df)` — exactly as specified in
`fx_backtester_spec.md` §2.2, unchanged. This visualizer needs four
**additions** to that same class, purely additive (no existing method's
behavior, signature, or the class's abstract-ness changes):

```python
class Strategy(ABC):
    # ... existing sl_pips, tp_pips, exit_on_opposite_signal, generate_signals()
    # unchanged, exactly as already built ...

    # NEW -- column-rendering metadata for visualize() below. Every column
    # generate_signals() adds that should be inspectable on a chart must be
    # declared here explicitly -- undeclared columns are simply not plotted,
    # never silently guessed at (same "explicit wins" principle used
    # throughout this project). "candle" columns need no declaration --
    # auto-detected from standard OHLC column names. A region entry can also
    # describe a bounded box rather than full-height shading -- see §5.1.
    line_columns: list[str] = []      # e.g. ["sma_fast", "sma_slow"]
    marker_columns: list[str] = []    # e.g. ["long_signal", "short_signal"]
    region_columns: list[str] = []    # e.g. ["trend_direction"]

    # NEW -- concrete, not abstract. Subclasses declare the three lists
    # above and inherit this for free; override only for genuinely custom
    # rendering needs. Full mechanics (chart reuse for hot-reload, the
    # show_trades trade-overlay projection, performance guidance) in §8
    # below -- this is the primary interface for visualization, not a
    # deferred nice-to-have.
    def visualize(self, engine, chart=None, show_trades=False):
        """Must lazy-import the chart package inside this method body
        (`from fx_viz import FxChart`), never at this module's top level --
        headless backtests, parameter sweeps, and CI must never pay for or
        fail on a GUI/notebook-widget dependency they don't use."""
```

Existing strategies (e.g. `SmaCrossoverStrategy`, already built) need no
changes to keep working — the three new list attributes default to empty,
and `visualize()` on a strategy that hasn't declared any of them just renders
a bare candle chart with nothing overlaid. Adding chart support to an
existing strategy is purely additive: set the three class attributes,
nothing else changes.

---

## 3. Hot-reload contract (items 3/4)

Same two-cell pattern as the first draft, still the right shape for this part:

```python
# CELL 1 -- once per session
from fx_viz import FxChart
chart = FxChart()
chart
```

```python
# CELL 2 -- rerun every time indicator/signal code changes
df = my_strategy.generate_signals(raw_df)
chart.plot(df, spec=[
    {"column": "close", "kind": "candle"},
    {"column": "sma_fast", "kind": "line", "color": "#E8A33D"},
    {"column": "long_signal", "kind": "marker", "shape": "arrowUp"},
    {"column": "rsi", "kind": "line", "pane": 1},   # see §3 -- routed to its own sub-window
])
```

**Requirement, stated explicitly since it's easy to get wrong**: re-running
Cell 2 must update the existing chart **without resetting the current
zoom/pan/timeframe view** — a strategy-code edit shouldn't yank you back to
some default view every time you want to see the effect of the edit. This is
the same "declarative, full-state, but the viewport is independent of the
data" principle a real dev tool needs — closer to how a debugger keeps your
scroll position while you step through code than to a full page reload.

---

## 4. Multi-pane routing (item 6) and timeframe switching (item 7)

- `spec` entries take an optional `"pane"` key (integer, default `0` = the
  main price pane). Same declarative column-generic contract as before —
  routing to a separate pane is just another property of a spec entry, not a
  different code path. `{"column": "rsi", "kind": "line", "pane": 1}` and
  `{"column": "atr", "kind": "line", "pane": 2}` would each get their own
  sub-window below the main price pane, in the order first referenced.
- Timeframe switching lives as **native UI in the chart itself** (using the
  underlying library's built-in timeframe-selector events per §1), not a
  separate Python-side control. When the user clicks a timeframe in the
  chart, that fires an event Python subscribes to; Python resamples the
  currently-loaded base data (or fetches a new window, see §4) to the
  requested timeframe and re-renders. The currently-active `spec` (whichever
  indicators/signals are plotted) must be recomputed against the new
  timeframe's data before rendering — switching timeframe without
  recomputing signals would silently show stale/wrong indicator values, which
  is a correctness bug, not just a UX rough edge.

---

## 5. Lazy loading (item 8)

**The core mechanism**: Python holds (or has fast access to) the full
underlying dataset; the chart only ever holds a window of it. As the user
pans toward the edge of the currently-loaded window, or switches timeframe,
the chart requests more data rather than the widget ever being handed the
full dataset upfront.

- Subscribe to the library's visible-range-changed event (confirm exact hook
  during the §1.1 spike). When the visible range approaches within some
  margin of the currently-loaded window's edge, trigger a Python-side fetch
  for the next chunk (a fixed number of bars, or a fixed time span) and
  prepend/append it to what's loaded, without disturbing the currently
  visible bars or the user's viewport position.
- This is the same **"caller must slice before plotting"** principle from the
  first draft's §4, just automated: instead of asking the notebook user to
  manually pick a window before calling `.plot()`, the chart manages its own
  window and asks Python for more as needed. The user-facing `.plot(df,
  spec)` call can still take a full dataset reference (or a data-access
  function/object capable of returning a slice for a given time range and
  timeframe) rather than requiring a pre-sliced dataframe — that's the
  concrete difference from the first draft's data-handling contract.
- Indicator/signal recomputation has to follow the same lazy pattern: when a
  new chunk of underlying data loads, the current strategy's
  `generate_signals()` needs to run on it (extended appropriately for any
  warmup window, e.g. don't compute an SMA(50) on a freshly-loaded chunk
  without also pulling the ~50 bars immediately before it) before the new
  chunk is handed to the chart — otherwise indicator values would show
  visible seams at chunk boundaries.

---

## 6. Column contract (unchanged from first draft, still correct)

- `kind: "candle"` — needs OHLC columns (default guess `open/high/low/close`).
- `kind: "line"` — numeric column, drawn as an overlaid or paned line series.
- `kind: "marker"` — boolean column, `True` rows get a marker glyph.
- `kind: "region"` — boolean/small-cardinality categorical column, contiguous
  runs shaded as background bands. Native support unclear even in v5 — same
  candidate-technique list as the first draft (plugin/primitives API, HTML
  overlay div, or filled-area fallback) remains the right approach; resolve
  empirically during implementation, now checking whether `python-lightweight
  -charts`' plugin support (mentioned in its feature list) already covers
  this before building a custom overlay.
- `spec` optional; default heuristic by dtype, explicit entries always
  override. Unchanged reasoning from the first draft.

### 6.1 Horizontal lines and boxes — both still column-driven, corrected design

An earlier draft of this section proposed two separate `Strategy` methods
(`get_hlines`/`get_boxes`) outside the column contract, reasoning that
neither fits the "one value per bar" shape. That reasoning was wrong — both
fit naturally once you notice every row already carries a (time, price) pair,
which is exactly what both of these need:

- **Horizontal line**: nothing new at all. It's a `line`-kind column whose
  value happens to be constant across every row (e.g. a strategy that wants
  to mark "yesterday's high" computes one column, same value repeated for
  every bar of the day — trivial with a single `with_columns(pl.lit(...))`
  call). The chart draws it with the exact same code path as `sma_fast` —
  it just looks flat because the value doesn't change. No new render logic,
  no new declaration mechanism beyond `line_columns`.
- **Box**: an extension of `region`, not a new kind. Region rendering already
  does contiguous-run detection on a column (find where the value changes,
  treat each run as one shaded span) — a box is the same run-detection, plus
  two companion numeric columns giving the top/bottom price bounds for that
  run, rendered as a bounded rectangle instead of full-chart-height shading.
  A `spec` entry can optionally carry `top_column`/`bottom_column`:
  ```python
  {"column": "consolidation_zone", "kind": "region",
   "top_column": "zone_top", "bottom_column": "zone_bottom"}
  ```
  `zone_top`/`zone_bottom` should hold a constant value across each run (the
  renderer can just read the first non-null value found within the run).
  Omitting `top_column`/`bottom_column` falls back to the original
  full-height region behavior (session shading, trend shading) — this is a
  strictly backward-compatible extension, not a competing mechanism.

Net effect: **no new `Strategy` methods, no exception to the column
contract.** `line_columns`/`marker_columns`/`region_columns` remain the
entire declaration surface.

**Bounded vs. unbounded lines — also free, same null convention.** A `line`
column filled on every row (no nulls) renders as spanning the whole loaded
range. A column that's `null` outside some stretch and constant within it
renders as a bounded segment — starts and stops exactly where the values do,
no separate start/end fields needed. **Verify during implementation which
way the underlying chart library treats `null` in a line series** — it must
render as a genuine gap (line stops, resumes later), not interpolate straight
through and reconnect the two sides. If the library defaults to
interpolating across gaps, that setting needs to be explicitly turned off, or
a bounded hline would silently render as misleadingly continuous.

---

## 7. Principles (unchanged, still the actual bar)

1. Declarative, not imperative — `.plot(df, spec)` fully describes desired
   state each call.
2. Idempotent — same inputs, same rendered result, no accumulation.
3. The widget instance persists across cell reruns; **and now, the viewport
   persists across data updates too** (§2) — both are the feature, not
   incidental behavior.
4. Zero indicator-specific code in the visualization layer — new column, new
   `spec` entry, no code change.
5. No required runtime network dependency for the core chart (vendor the JS
   library regardless of which Python wrapper delivers it).

---

## 8. `Strategy.visualize()` — primary interface, not a follow-on

**Revised from earlier drafts of both specs, which called this an optional
later add-on. It isn't — it's the main way this tool gets used, since real
work happens through a `Strategy` subclass, not raw dataframe manipulation.**
`Strategy.visualize()` is specified as a patch to the existing class in §2
above; this section specifies what it actually does at runtime.

```python
strategy.visualize(engine, chart=None, show_trades=False)
```

### 8.1 Why it takes `engine`, not a raw `df`

`Engine` already owns the sanity-checked data (§2.1 of the backtester spec) —
`visualize()` needs `engine.df` to run `generate_signals()` against, and (when
`show_trades=True`) needs to call `engine.backtest(self)`. Requiring the
caller to juggle a separate df and a separately-run trades log is exactly the
manual bookkeeping this method exists to eliminate. One argument, everything
`visualize()` needs comes from it.

### 8.2 The `chart` parameter and hot-reload

- **`chart=None`** (default): creates a fresh `FxChart`, displays it. Fine for
  a single quick look in one cell, but a new widget each call means no
  viewport is preserved across reruns — not the hot-reload pattern.
- **`chart=<existing FxChart>`**: reuses it. This is the pattern for the
  actual iterate-on-strategy-code loop:

```python
# Cell 1 -- once
chart = FxChart()
chart
```
```python
# Cell 2 -- rerun every time strategy code changes
strategy = MyStrategy(fast_n=20, slow_n=50, sl_pips=10, tp_pips=20)
strategy.visualize(engine, chart=chart)
```

Same viewport-preservation requirement as §2 — editing `MyStrategy` and
rerunning must not reset zoom/pan/timeframe.

### 8.3 Building the spec automatically

`visualize()` never hand-writes a `spec` list itself — it derives one purely
from the strategy's declared `line_columns`/`marker_columns`/`region_columns`
class attributes (§2 above, including the box extension in §6.1), plus
automatic OHLC-column detection for the candle series.
This is a direct, mechanical mapping: a strategy that declares `line_columns
= ["sma_fast", "sma_slow"]` gets exactly those two columns plotted as lines,
no more, no less. If a strategy adds a debugging column to its dataframe but
doesn't declare it, it's simply absent from the chart — silent by omission
is the correct failure mode here (matches the "explicit wins" principle used
everywhere else in this project), not a crash and not a guess.

### 8.4 `show_trades=True` — the trade-overlay projection

When enabled, `visualize()`:
1. Runs `trades = engine.backtest(self)`.
2. **Projects `trades` onto the signal-timeframe df as new marker/region
   entries** — this is genuinely new logic, since trade data doesn't exist
   until after a backtest runs, so it can't come from `generate_signals()`'s
   own declared columns:
   - A **point marker** at each trade's `entry_time` (distinct shape/color
     from the raw signal markers, so "a crossover fired here" and "a trade
     was actually taken here" stay visually distinguishable — they can differ,
     since not every signal necessarily produces a trade depending on
     position state).
   - A **region** spanning `entry_time` → `exit_time` for each trade, colored
     by side (long/short) and/or `exit_reason` (SL/TP/opposite
     signal/end_of_data) — reusing the existing region-rendering mechanism,
     no new chart-side code needed. This turns "was this fill even sane"
     (the §6 regression-investigation habit from earlier) into something
     glanceable rather than something requiring a manual dataframe join.
3. These get merged into the auto-built `spec` from §8.3 before the single
   `chart.plot()` call — still one call, still one data model.

### 8.5 Performance — `show_trades` must default to `False`

Running a full backtest (including the numba 1s fill-resolution walk, §2.3
of the backtester spec) on every hot-reload would make the fast
signal-iteration loop (Phase 2 of the earlier workflow discussion) sluggish —
that loop's whole value is instant feedback while tuning signal logic, before
a trade-level audit is warranted. Default `show_trades=False` keeps that loop
fast; flip it on deliberately when you want the fuller audit view (Phase 4),
not on every rerun by default.

---

## 9. Out of scope

- Drawing tools (trendlines/rectangles) — `python-lightweight-charts`
  reportedly has a toolbox for this; not part of this spec's requirements,
  fine to ignore even if present.
- Order-entry/watchlist table features some charting libraries bundle —
  irrelevant to this project.

## 10. Explicit note for whoever implements this

Do the §1.1 spike **first**, before writing any of §2–§4's design into real
code. The whole plan here rests on `python-lightweight-charts`'s Jupyter
integration actually behaving the way its docs suggest for live, in-cell
updates — that's a real assumption, checked by search rather than hands-on
use, and it could be wrong in a way that only shows up once someone actually
tries the two-cell pattern in a real notebook. If it doesn't hold up, the
fallback (raw `anywidget` + vendored v5 JS, now knowing panes are natively
available) is documented above, not a dead end.
