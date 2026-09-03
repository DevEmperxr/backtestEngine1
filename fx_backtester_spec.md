# FX Backtester — Build Spec

**Status**: ready to hand off for implementation. This is the final spec from
a design session — all blocking decisions below are resolved. Where reasoning
is included, it's kept so a future change doesn't silently re-break something
that was deliberately chosen this way.

**Goal**: a small, transparent, reusable backtesting framework for FX
strategies — prioritizing correctness and debuggability over speed or
feature-count. Built by hand (not on top of vectorbt/backtrader/nautilus)
specifically so every timing/execution decision is visible and inspectable,
not hidden inside a library.

---

## 0. Prior art / reference semantics (must be preserved)

An earlier prototyping session (plain scripts, not yet the module structure
below) built and validated a working SMA-crossover backtest on 5-min EURUSD
bid/ask data, and got several subtle things right that **must carry over**
into this build, not be silently re-derived (and possibly re-broken):

1. **Timing model**: a signal computed using data through bar `t`'s close may
   only be acted on (entry, or exit-by-opposite-signal) at bar `t+1`'s open —
   the earliest realistic moment. Never act on a signal within the same bar
   it was generated.
2. **Within-bar event ordering**: a bar's OPEN happens first (signal-based
   entries/exits execute here), THEN price moves through the bar's range (SL/TP
   checked here). A position that exits via signal at the open is not exposed
   to that same bar's intrabar SL/TP — it's already flat before the range
   unfolds. (A real bug was caught and fixed here during prototyping — getting
   this ordering wrong silently let SL/TP fire on bars where a signal-exit
   should have preempted them.)
3. **Spread-correct fills**: buys (long entry, short exit) fill at ASK; sells
   (short entry, long exit) fill at BID. Never use mid-price for execution,
   only for signal computation.
4. **Boolean dtype trap**: `some_bool_series.shift(1)` introduces a leading
   `NaN`, silently upcasting the column to `object` dtype. `~` (invert) on an
   `object`-dtype column of Python `bool`s does **bitwise** invert on the
   underlying ints (`~True == -2`, `~False == -1`), both truthy — silently
   breaking any crossover-style logic built on it. Always use
   `series.shift(1, fill_value=False)` (or explicit `.astype(bool)` after)
   to keep a real boolean dtype. This exact bug produced a 44x-inflated signal
   count during prototyping and should have a regression test guarding it
   (see §6).
5. **Sanity-check discipline on any new data**: no duplicate timestamps, no
   nulls, OHLC internally consistent (`high >= max(open,close,low)`, `low <=
   min(open,close,high)`), gaps explained (weekends/holidays — flag anything
   else), spread (`ask - bid`) never negative.

These aren't stylistic preferences — each one was a real bug or near-bug
during prototyping. Implement them as explicit, commented logic (and ideally
as unit tests), not as something to rediscover.

### 0.1 A principle worth stating outright: two different uses of "future" data

The engine legitimately touches data timestamped after a decision point in
one specific way, and it's easy to conflate this with an actual lookahead bug
if it isn't named explicitly:

- **Illegal**: using data timestamped after bar `t`'s close to help DECIDE
  what happens at bar `t` (i.e. to compute a signal, or to choose an entry
  price). This is what "no lookahead" means, and it is never allowed anywhere
  in `signals.py` or in how the engine times entries.
- **Legal and necessary**: once a decision has already been made (a trade has
  been entered), simulating what happens to it afterward necessarily involves
  data timestamped after entry — this is true of any backtest, at any
  granularity (checking bar `t+2`, `t+3`... for an exit is already "future"
  relative to entry). Resolving fills against the 1-second path (§2.3) is
  this same, ordinary thing, just at finer resolution than before. It is not
  a form of lookahead bias, because it never influences a decision — it only
  measures the consequence of one already made.

If in doubt about a specific piece of logic: ask whether that data could have
changed which trade was taken, or only how an already-taken trade played out.
Only the former is a lookahead risk.

---

## 1. Data layer

- **Instrument**: EURUSD, bid and ask loaded/tracked separately throughout.
- **Base granularity**: **1-second candles**, ~1 year of history, already
  available locally (user has the files; exact path/filenames TBD at build
  time — assume same schema as the earlier 5-min prototype files unless the
  actual files say otherwise: columns `timestamp, open, high, low, close`,
  one file for ASK one for BID, UTC timestamps).
- **Library**: **polars** for loading, cleaning, and resampling. Pandas is not
  used at the data layer.
- **All coarser timeframes are derived from the 1s base via resampling** (5m,
  1H, 4H, etc.) — not loaded/stored as separate files.
- Apply the sanity checks from §0.5 on load, at 1s resolution. At ~31M rows,
  make sure these checks are vectorized polars expressions, not row-wise
  Python — this matters at this scale.

**Module**: `data.py`
```python
def load_1s_data(ask_path: str, bid_path: str) -> pl.DataFrame:
    """Loads, sanity-checks, and returns cleaned 1s bid/ask data.
    Raises on: duplicate timestamps, nulls, broken OHLC, negative spread.
    Logs/returns gap info (weekend gaps expected; anything else is a warning)."""

def resample(df: pl.DataFrame, timeframe: str) -> pl.DataFrame:
    """Aggregates 1s base data to a coarser timeframe (e.g. '5m', '1h', '4h').
    Bucket convention: label=left, closed=left (bucket starting at HH:MM:00
    covers [HH:MM:00, HH:MM:00+timeframe)). Must preserve bid AND ask OHLC
    separately (open=first, high=max, low=min, close=last, per side).

    TWO CORRECTNESS REQUIREMENTS, both directly guard against lookahead bugs:

    1. Must also return (or make derivable) each bar's "close time" = its
       label timestamp + the timeframe's duration. This is NOT always
       "+5 minutes" -- the old 5-min-only prototype hardcoded that because
       the timeframe never varied; here the engine's timing rule (a bar's
       data is knowable only once it's fully closed) must be computed from
       the actual `timeframe` argument, generalized, for every call site.
       A stale hardcoded assumption here IS a lookahead bug -- e.g. treating
       a 1-hour bar as "closed" 5 minutes after it opened.

    2. Must DROP the trailing partial bucket if the 1s data doesn't end
       exactly on a timeframe boundary. That last bucket never actually
       finished -- it holds whatever 1s ticks existed before the dataset ran
       out, not a genuinely closed candle. Including it lets a strategy
       compute a "confirmed" signal from a candle that, in live trading,
       would still be half-formed. Check `bucket_start + timeframe <=
       max(1s timestamp) + 1s`; drop any bucket that fails this.
    """
```

---

## 2. Backtest engine

**Module**: `engine.py`

### 2.1 `Engine`
```python
class Engine:
    def __init__(self, df):
        """df: polars or pandas DataFrame already loaded/cleaned (this class
        does NOT call load_1s_data() itself -- loading is a separate concern,
        done externally, so Engine stays agnostic to instrument/timeframe/
        loading-library choices). Sanity-checks whatever it's handed at
        construction time (same checks as §0.5) -- fails loudly if the df
        wasn't actually cleaned upstream.

        Also holds a reference to the 1-second base data (or is handed it
        alongside df) -- required for fill resolution, see 2.3.
        """

    def backtest(self, strategy: "Strategy") -> trades_df: ...
    def evaluate(self, trades_df) -> dict: ...  # see §3
```

### 2.2 `Strategy` (formal interface)
```python
from abc import ABC, abstractmethod

class Strategy(ABC):
    # SL/TP are constructor params on the strategy instance -- part of what
    # defines a specific strategy variant, not a separate engine-run argument.
    # e.g. SmaCrossoverStrategy(fast_n=20, slow_n=50, sl_pips=10, tp_pips=20)
    sl_pips: float
    tp_pips: float

    # Whether the engine should also exit a position when the OPPOSITE signal
    # fires (in addition to SL/TP). Default True. A future strategy that should
    # ONLY exit via SL/TP (or some other exit rule) can set this False.
    exit_on_opposite_signal: bool = True

    @abstractmethod
    def generate_signals(self, df):
        """Pure function: df in -> df out with AT MINIMUM long_signal and
        short_signal boolean columns added. May add any number of other
        columns (SMA values, trend_direction, session flags, etc.) -- those
        are free for debugging/visualization use, the engine only reads the
        two signal columns and the exit_on_opposite_signal flag.

        Responsible for its own no-lookahead correctness: a value at row t
        may only use information available through bar t's close. (The
        ENGINE separately enforces the "acted on at t+1" timing rule --
        these are two different responsibilities, both required, see §0.1/§0.2.)

        IMPORTANT: "bar t's close" means bar_start_timestamp + this
        strategy's timeframe duration -- NOT a hardcoded +5 minutes. Since
        different strategies may operate on different resampled timeframes
        (5m, 1h, 4h...), this must be computed generically from whatever
        timeframe generate_signals() actually operates on. See resample()'s
        docstring in data.py for the matching requirement on the data side.
        """
```

### 2.3 Fill resolution — 1-second path (decided)

Signals are computed on the aggregated timeframe the strategy actually uses
(e.g. 5-min bars, via `resample()`). But once a trade is opened, **the engine
resolves its SL/TP by walking the real underlying 1-second price path between
entry and exit**, rather than checking SL/TP against the signal-timeframe
bar's OHLC range. This replaces the earlier prototype's "assume SL hit first"
same-bar-ambiguity approximation with the actual resolved order of events --
we now know, don't have to guess.

Consequence: `backtest()`'s execution loop iterates the (small) signal-
timeframe df for signal/entry timing, but for each open trade, slices and
walks the 1-second data between that trade's entry and exit timestamps to
find the real first-touch of SL or TP.

**Performance**: this per-trade 1s walk is the likely bottleneck (potentially
thousands of trades × up to hours-long holds, over ~31M base rows).
**Decided: implement this inner walk with `numba` (`@njit` on a plain
imperative loop over a numpy array slice)** -- deliberately NOT a vectorized/
pandas-native rewrite. The reason is the same one that mattered during
prototyping: an imperative, step-by-step loop keeps every timing decision
visible and debuggable; a vectorized approach makes exactly this kind of
bug (silently wrong event ordering) easy to hide. Numba gets the speed
without giving up that transparency -- the loop body should read almost
identically to a plain Python loop, just JIT-compiled.

Outer loop (signal-timeframe iteration, entry/exit-by-signal timing) can
remain plain Python/pandas-or-polars -- it operates on the much smaller
aggregated row count, not the 31M base rows, so it isn't the bottleneck.

### 2.4 Other engine behaviors (decided)

- **Position sizing is out of scope for the engine.** Trades are tracked in
  pips only, position-agnostic. Lot size / risk-% sizing is purely an
  `evaluate()`-time input for converting pips to $ -- neither `Engine` nor
  `Strategy` needs to know about it.
- **End of data with an open position**: force-close at the last available
  price, tag `exit_reason='end_of_data'` in the trade log (never silently
  drop an open position -- that would bias total P&L).
- **Multi-instrument generality is explicitly deferred.** Pip size (0.0001)
  and pip-value math are hardcoded for EURUSD. Do not generalize this
  pre-emptively for other pairs/quote-currencies until there's an actual
  second instrument in scope -- premature abstraction here isn't worth it yet.

---

## 3. Evaluation

**Module**: `evaluate.py`, exposed as `Engine.evaluate(trades_df)`.

Build **both** tiers now, not just the "normal" one -- this was an explicit
priority call, directly motivated by wanting the framework to actively resist
the "backtest lied to me" failure mode rather than just warn about it in
prose.

### 3.1 Normal metrics (already prototyped once, port the logic)
- Equity curve (cumulative pips, and $ given a passed-in position size / starting
  balance -- these are `evaluate()` args, not engine state)
- Max drawdown (%, and date of trough)
- Sharpe ratio, Sortino ratio (annualized, from daily-aggregated returns;
  document the rf=0 assumption)
- MAR ratio (CAGR / max drawdown)
- Win rate, expectancy (pips/trade), profit factor, avg win/loss
- Monthly P&L breakdown (table + bar chart)

### 3.2 Adversarial metrics (new requirement -- must be present, not optional)
- **Confidence interval on win rate and expectancy**, computed via **bootstrap
  resampling** (resample trades with replacement, thousands of times, take the
  spread of the resulting statistic) rather than a normal-approximation
  formula -- more robust when the trade P&L distribution is skewed/fat-tailed,
  which is plausible here given a fixed-size TP but variable-sized
  signal-exit losses.
- **Monte Carlo trade-order shuffling.** Take the actual sequence of realized
  trade P&Ls from the backtest and randomly reshuffle their *order* (not their
  values) thousands of times, recomputing the equity curve and max drawdown
  for each shuffled ordering. Report the distribution of max drawdown across
  all shuffles (e.g. median, 95th percentile, worst-case), not just the single
  drawdown number the actual historical ordering happened to produce.
  Answers: "was my reported drawdown just luck of the sequence, or is the
  strategy fragile in a way the one real ordering happened to hide?" A
  strategy whose real-history drawdown looks tame but whose shuffled
  distribution shows a much worse drawdown in a meaningful fraction of
  reorderings should be flagged as fragile, even though the single backtest
  run looked fine.
  - Important scope note: this reshuffles the *trades you already have* — it
    tests sequence-risk, not "would this work on different data." It cannot
    detect an edge that doesn't exist; it only reveals whether a real edge's
    reported risk profile was flattering due to a lucky ordering. Don't let a
    good shuffle distribution be read as validating the strategy itself — that
    still depends on the sample-size and cost-decomposition checks above it.
- **P&L with the single best month excluded** -- surfaces whether the result
  depends on one lucky stretch.
- **P&L with the best N trades excluded** (N configurable, e.g. top 1%/5%) --
  same idea at the trade level.
- **Gross-vs-net cost decomposition**: total spread cost paid vs. gross P&L
  before costs, so "the edge was real but costs ate it" is distinguishable
  from "there was no edge."
- **Sample-size warning**: below some trade-count threshold (e.g. 100),
  `evaluate()` must prominently flag that the result's precision is
  low -- not bury it in a footnote. Consider refusing to print an
  unqualified "profitable" or "unprofitable" verdict below the threshold.

---

## 4. Strategies

**Module**: `strategies.py`. Each strategy is a small, explicit `Strategy`
subclass -- composition of signal-generating logic, not a config-driven
generic system (deliberately -- a declarative/config-driven strategy definition
invites parameter-twisting/overfitting; explicit code stays legible and keeps
a human making each decision). First strategy to port over: the SMA(20/50)
crossover with fixed SL/TP, exactly as prototyped, as the reference/regression
case (see §6).

**Module**: `signals.py`. Pure functions/composable pieces that
`generate_signals()` implementations call into (e.g. SMA crossover detection,
4H trend filter via lookahead-safe `merge_asof`, session-window flag). Signal
functions may leave behind intermediate columns (SMA values, `trend_direction`,
etc.) -- useful for debugging and for the (deferred) visualizer, not just
scratch space to discard.

---

## 5. Visualizer -- explicitly deferred, not part of this build

Requirements below are captured for later, so they aren't lost, but **should
not be built in this pass**. Framework (data/engine/strategies/evaluate) comes
first; revisit this section once that's solid.

- **Chart navigation**: timeframe selector (view any resampled timeframe on
  demand); replay controls (rewind/play/pause/step, roughly video-like) so
  signals can be watched firing bar-by-bar rather than only viewed with
  hindsight on a finished chart.
- **Signal rendering**: one data model, two render styles, chosen per-column,
  not two different signal types:
  - *Point-style*: columns that are mostly False, flip briefly True at
    isolated bars (e.g. a crossover) -> marker/arrow at that bar.
  - *Region-style*: columns that hold constant across long contiguous runs
    (e.g. `trend_direction`, session-window flags) -> shaded background /
    zone spanning each run's start to end (or a state sub-pane). Note: some
    of these columns are categorical, not boolean (e.g. `trend_direction` in
    {'up','down',None}) -- region rendering needs a color-per-category rule,
    not just an on/off shade.
- **`Strategy.visualize(df)` API**:
  - Thin delegator only -- actual rendering lives in its own module (`viz.py`),
    the only file importing the charting library, imported lazily inside
    `visualize()` (so headless backtests/CI never pay for or fail on a GUI
    dependency).
  - Never recomputes signals -- takes a df that already has the columns
    `generate_signals()` produced, same as what `backtest()` consumed. No
    parallel "figure out what to draw" logic that could silently diverge from
    what was actually traded on.
  - Point/region/line classification is explicit per-strategy metadata
    (`point_columns`, `region_columns`, `line_columns` class attributes),
    not auto-inferred from run-length.
  - Subclassing composes naturally (a filtered strategy inherits the base's
    `visualize()` and column lists, adds its own).
- **Chosen library**: `lightweight-charts-python` (wraps TradingView's actual
  open-source Lightweight Charts JS engine). Standalone desktop window
  (pywebview) for fast dev-loop use now; explicitly supports Streamlit as an
  environment for a later persistent dashboard, or migrate at that point to
  the purpose-built `streamlit-lightweight-charts-pro` component (same
  underlying JS engine, more Streamlit-native API). Ruled out: PyGWalker (no
  time-series/candle concept), Streamlit alone (right tool later, not for
  fast iteration now). Fallback alternatives if needed: `finplot` (PyQtGraph,
  fast, similar crosshair/OHLC-on-hover), Plotly candlestick (most portable).
- **Design decision from the visualization discussion**: since 1s is the base
  data, consider decoupling *what's displayed* from *what's traded on* --
  play back the real 1-second candles (tactile, intuition-building) while
  signals themselves are computed and overlaid from a coarser aggregated
  timeframe. Don't compute signals directly on 1s data; that's a timeframe
  where spread cost dominates any plausible signal.
- Not yet decided (fine to leave open until this section is picked back up):
  replay playback speed/step granularity; exact per-column style-tagging
  mechanism (explicit list vs decorator vs dict).

---

## 6. Validation strategy

- **Regression test against the known baseline.** The SMA(20/50) crossover
  strategy, on 5-min EURUSD bars, previously produced **1,691 trades, −346.5
  total pips, 33.0% win rate** (prototyped against a 5-min dataset covering
  2024, with the OLD signal-timeframe-only fill resolution / "assume SL
  first" approximation).
  - Rebuild the equivalent 5-min bars **by resampling the new 1s base data**
    (§1) and re-run the same strategy through the new engine.
  - **Do not expect an exact match** to the old numbers -- the new engine
    resolves fills against the real 1s path (§2.3) instead of guessing on
    same-bar SL/TP ambiguity, so previously-ambiguous trades may now resolve
    differently (this is the new engine being *more* correct, not a bug).
  - What SHOULD match closely: total trade count, entry timestamps/prices,
    and the broad shape of the result (still a small negative edge). A large,
    unexplained deviation (materially different trade count, sign flip, wildly
    different pip total) signals a real bug in the new pipeline, not just
    fill-resolution refinement -- investigate before trusting anything else.
  - Also add the narrower unit-level regression from §0.4 directly: assert
    that a boolean-crossover helper produces a real `bool`-dtype result and a
    sane signal count on a small synthetic series, so that specific dtype bug
    class can never silently reappear.
  - **Add a direct lookahead test for `resample()`**: on synthetic 1s data,
    assert (a) the trailing partial bucket is dropped when the data doesn't
    end on a clean boundary, and (b) for a couple of different `timeframe`
    values (not just 5m), a bar's "close time" is correctly computed as
    `bucket_start + timeframe`, not a stale hardcoded duration. This directly
    guards the gap identified in §1/§2.2 during spec review.

---

## 7. Explicitly out of scope for this build

- 1-second-resolution *signals* (only used as base data for resampling + fill
  resolution, not as a strategy's own timeframe)
- The visualizer (§5) in its entirety
- Multi-instrument support beyond EURUSD
- Position sizing / risk-% logic beyond raw pip tracking
