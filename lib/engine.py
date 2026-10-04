"""Backtest engine (spec §2).

Contains the `Strategy` ABC (§2.2) and `Engine` (§2.1), plus the numba 1s-path
SL/TP resolver (`_resolve_exit`, §2.3). `backtest` is complete: rising-edge
entries with t+1 timing (§0.1), spread-correct fills (§0.3), and per-trade exit
resolved on the real 1s path — SL / TP / opposite-signal / end-of-data, with the
within-bar ordering of §0.2 respected.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import polars as pl
from numba import njit

from lib.data import PIP, resample, validate_1s

_PRICE_COLUMNS = tuple(
    f"{side}_{field}"
    for side in ("bid", "ask")
    for field in ("open", "high", "low", "close")
)

# _resolve_exit reason codes
_NO_TOUCH = 0
_HIT_SL = 1
_HIT_TP = 2


@njit(cache=True)
def _resolve_exit(exit_high, exit_low, start_idx, end_idx,
                  direction, sl_level, tp_level):
    """Walk the 1s path [start_idx, end_idx) for the first SL or TP touch.

    `exit_high` / `exit_low` are the 1s high/low of the side the trade exits
    *against* (spec §0.3): a long exits by selling, so the caller passes the BID
    arrays; a short exits by buying, so the caller passes the ASK arrays. This
    function neither knows nor cares which side it was handed.

    direction: +1 long, -1 short.
      long : SL when exit_low[k]  <= sl_level ; TP when exit_high[k] >= tp_level
      short: SL when exit_high[k] >= sl_level ; TP when exit_low[k]  <= tp_level
    Touches are inclusive.

    Returns (hit_idx, exit_price, reason_code):
        reason 0 (_NO_TOUCH) -> hit_idx == end_idx, exit_price == 0.0
        reason 1 (_HIT_SL)   -> hit_idx == k, exit_price == sl_level
        reason 2 (_HIT_TP)   -> hit_idx == k, exit_price == tp_level

    exit_price is the level itself — we model a resting stop / limit order that
    fills at its price, not at the traded extreme.

    If a single 1s bar's [low, high] straddles BOTH levels, SL wins. This is the
    spec's old "assume SL hit first" tie-break, but now it only bites within one
    second of price action rather than across a whole signal-timeframe bar, so
    it is rare and its cost is bounded.
    """
    for k in range(start_idx, end_idx):
        if direction == 1:
            sl_hit = exit_low[k] <= sl_level
            tp_hit = exit_high[k] >= tp_level
        else:
            sl_hit = exit_high[k] >= sl_level
            tp_hit = exit_low[k] <= tp_level

        if sl_hit:
            return k, sl_level, _HIT_SL
        if tp_hit:
            return k, tp_level, _HIT_TP

    return end_idx, 0.0, _NO_TOUCH


def _sl_tp_levels(direction, entry_price, sl_pips, tp_pips, pip=PIP):
    """Absolute SL/TP price levels for a position.

    long  (+1): SL below entry, TP above.
    short (-1): SL above entry, TP below.

    Returns (sl_level, tp_level).
    """
    offset_sl = sl_pips * pip
    offset_tp = tp_pips * pip
    if direction == 1:
        return entry_price - offset_sl, entry_price + offset_tp
    return entry_price + offset_sl, entry_price - offset_tp


def _windowed_signals(
    strategy: "Strategy", bars: pl.DataFrame, start_idx: int, end_idx: int, warmup_bars: int
) -> pl.DataFrame:
    """`generate_signals()` over `[start_idx, end_idx)`, extended backward by
    up to `warmup_bars` so indicators (SMA, etc.) aren't seamed/null right at
    the loaded edge (visualizer spec §5).

    No-lookahead by construction: `compute_start = max(0, start_idx -
    warmup_bars)` is always <= `start_idx`, so the extra rows fed to
    `generate_signals()` are strictly history relative to what gets returned
    -- never `end_idx` or beyond. The warmup rows themselves are sliced back
    off before returning; they exist only to seed rolling calculations, never
    to be shown or used again. `generate_signals()` is called unmodified, so
    its own §0.1-§0.4 no-lookahead contract is untouched by this.
    """
    compute_start = max(0, start_idx - warmup_bars)
    raw = bars.slice(compute_start, end_idx - compute_start)
    full = strategy.generate_signals(raw)
    return full.slice(start_idx - compute_start, end_idx - start_idx)


def _project_trades(df: pl.DataFrame, trades: pl.DataFrame) -> pl.DataFrame:
    """Project a trade log onto `df` as new boolean columns (visualizer §8.4):
    `trade_entry_long`/`trade_entry_short` (True at each trade's entry bar) and
    `trade_region_long`/`trade_region_short` (True for every bar inside a
    trade's [entry_time, exit_time) window). Relies on `Engine.backtest`'s
    guarantee that trades never overlap in wall-clock time, so an asof-backward
    join unambiguously attributes each bar to at most one open trade.
    """
    by_entry = trades.sort("entry_time")
    joined = df.join_asof(
        by_entry.select("entry_time", "exit_time", "direction"),
        left_on="timestamp", right_on="entry_time", strategy="backward",
    )
    in_trade = (joined["timestamp"] >= joined["entry_time"]) & (
        joined["timestamp"] < joined["exit_time"]
    )
    direction = joined["direction"]
    return df.with_columns(
        trade_entry_long=df["timestamp"].is_in(
            trades.filter(pl.col("direction") == "long")["entry_time"].implode()
        ),
        trade_entry_short=df["timestamp"].is_in(
            trades.filter(pl.col("direction") == "short")["entry_time"].implode()
        ),
        trade_region_long=(in_trade & (direction == "long")).fill_null(False),
        trade_region_short=(in_trade & (direction == "short")).fill_null(False),
    )


class Strategy(ABC):
    """Formal strategy interface (spec §2.2).

    A concrete strategy is a small subclass that implements `generate_signals`.
    SL/TP and the timeframe are part of what *defines* a strategy variant, so
    they are constructor args, not engine-run arguments. A subclass calls
    `super().__init__(...)` then adds its own params (e.g. `fast_n`, `slow_n`).

    Attributes
    ----------
    sl_pips : float
        Stop-loss distance in pips (> 0).
    tp_pips : float
        Take-profit distance in pips (> 0).
    timeframe : str
        Resampled timeframe this strategy operates on ("5m", "1h", ...). Drives
        the no-lookahead "bar t's close" calculation below.
    exit_on_opposite_signal : bool, class attribute, default True
        Whether the engine also closes an open position when the opposite signal
        fires, on top of SL/TP. Set False on a subclass to exit only via SL/TP.
    reverse_on_opposite_signal : bool, class attribute, default False
        On an opposite-signal exit, immediately open the opposite position at the
        same bar/open ("always in the market"). Requires
        `exit_on_opposite_signal`. A trade that exits via SL/TP/end-of-data stops
        the reversal chain — the engine goes flat.
    """

    exit_on_opposite_signal: bool = True
    reverse_on_opposite_signal: bool = False

    # Column-rendering metadata for visualize() (visualizer spec §2). Every
    # column generate_signals() adds that should be inspectable on a chart
    # must be declared here explicitly -- undeclared columns are simply not
    # plotted, never silently guessed at. "candle" needs no declaration here
    # (visualize() auto-detects the bid_* OHLC columns).
    line_columns: list[str] = []
    marker_columns: list[str] = []
    region_columns: list[str] = []

    def __init__(self, sl_pips: float, tp_pips: float, timeframe: str) -> None:
        if not (sl_pips > 0):
            raise ValueError(f"sl_pips must be > 0, got {sl_pips!r}")
        if not (tp_pips > 0):
            raise ValueError(f"tp_pips must be > 0, got {tp_pips!r}")
        if not isinstance(timeframe, str) or not timeframe:
            raise ValueError(f"timeframe must be a non-empty str, got {timeframe!r}")
        if self.reverse_on_opposite_signal and not self.exit_on_opposite_signal:
            raise ValueError(
                "reverse_on_opposite_signal requires exit_on_opposite_signal"
            )
        self.sl_pips = float(sl_pips)
        self.tp_pips = float(tp_pips)
        self.timeframe = timeframe

    @abstractmethod
    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        """Pure signal computation: does not mutate `df`, returns a new frame.

        Must add at least two columns: `long_signal` and `short_signal`, both
        genuine `pl.Boolean` dtype. The engine trusts these are real booleans —
        this is exactly where the spec §0.4 boolean-dtype trap bites (a
        `.shift(1)` that upcasts to object and turns `~` into a bitwise op).

        May add any number of other columns (SMA values, `trend_direction`,
        session flags); the engine ignores them — they exist for debugging and
        the deferred visualizer.

        Responsible for its OWN no-lookahead correctness: a value at row `t` may
        only use information available through bar `t`'s close, where "bar `t`'s
        close" = `bar_start + self.timeframe` — computed from the actual
        timeframe, never a hardcoded +5m. The engine separately enforces the
        "act at `t+1`" timing rule; that is a different responsibility (§0.1).
        """

    def visualize(
        self,
        engine: "Engine",
        chart=None,
        show_trades: bool = False,
        *,
        initial_bars: int = 500,
        warmup_bars: int = 200,
        fetch_chunk: int = 500,
        edge_margin: float = 50,
        timeframes: tuple[str, ...] = ("1m", "5m", "15m", "1h", "4h"),
    ):
        """Chart this strategy against `engine`'s data (visualizer spec §8).

        `chart=None` creates and returns a fresh `FxChart` (displays it in the
        current cell). Pass an existing `FxChart` back in on a rerun to update
        it in place without resetting zoom/pan/timeframe (the hot-reload
        pattern — see fx_visualizer_widget_spec.md §3).

        `show_trades=False` by default: it runs a full backtest (including the
        numba 1s fill-resolution walk), which would make the fast
        signal-iteration loop sluggish if it ran on every rerun. Flip it on
        deliberately for the fuller trade-level audit view. The trade log
        itself is computed once here, never re-backtested on pan/timeframe
        switch (§8.5) -- only re-projected onto whatever window is showing.

        Lazy-loading (§5) and timeframe-switching (§4): only the last
        `initial_bars` bars are loaded at first; panning near a loaded edge
        (within `edge_margin` bars, via the chart's own `range_change` event)
        fetches another `fetch_chunk` bars on that side, and the native
        topbar switcher resamples `engine.base_1s` fresh and recomputes
        `generate_signals()` for the new timeframe, anchored on the same
        real-world moment that was at the right edge before the switch.

        No-lookahead discipline: every window handed to `generate_signals()`
        is extended by `warmup_bars` *strictly backward in time* (never
        forward) purely so indicators (SMA, etc.) have real history to warm up
        against instead of showing null/seamed values at the loaded edge --
        those extra rows are dropped again before anything is plotted. This
        mirrors the §0.1-§0.4 no-lookahead rules `generate_signals()` already
        has to satisfy on its own; nothing here bypasses or weakens that
        contract, it only ever slices strictly-historical data for it to run
        on.
        """
        from fx_viz import FxChart  # lazy -- headless backtests must never pay for this

        if chart is None:
            chart = FxChart()

        # A small distinct palette per declared column -- FxChart's own
        # per-kind default is a single fixed color, which makes multiple
        # auto-plotted lines/markers visually indistinguishable from each
        # other (confirmed: two un-colored sma lines render on top of each
        # other identically). Cycles if there are more columns than colors.
        _palette = ("#E8A33D", "#4C78A8", "#59A14F", "#B07AA1", "#E45756", "#76B7B2")

        def _spec() -> list[dict]:
            spec = [{"kind": "candle", "column": "bid"}]
            spec += [
                {"kind": "line", "column": col, "color": _palette[i % len(_palette)]}
                for i, col in enumerate(self.line_columns)
            ]
            spec += [
                {"kind": "marker", "column": col, "color": _palette[i % len(_palette)]}
                for i, col in enumerate(self.marker_columns)
            ]
            spec += [{"kind": "region", "column": col} for col in self.region_columns]
            if show_trades:
                spec += [
                    {"kind": "marker", "column": "trade_entry_long",
                     "shape": "arrow_up", "color": "#26A69A", "position": "below"},
                    {"kind": "marker", "column": "trade_entry_short",
                     "shape": "arrow_down", "color": "#EF5350", "position": "above"},
                    {"kind": "region", "column": "trade_region_long",
                     "color": "rgba(38, 166, 154, 0.12)"},
                    {"kind": "region", "column": "trade_region_short",
                     "color": "rgba(239, 83, 80, 0.12)"},
                ]
            return spec

        trades = engine.backtest(self) if show_trades else None
        spec = _spec()

        # Mutable closure state -- the currently-resampled full series for the
        # active timeframe, and which [start_idx, end_idx) slice of it is
        # currently loaded on the chart. Re-resampling the full engine.base_1s
        # only happens on a timeframe switch, never on an ordinary pan.
        state: dict = {}

        def _render(bars: pl.DataFrame, start_idx: int, end_idx: int) -> None:
            visible = _windowed_signals(self, bars, start_idx, end_idx, warmup_bars)
            if show_trades:
                visible = _project_trades(visible, trades)
            chart.plot(visible, spec=spec)
            state["bars"], state["start_idx"], state["end_idx"] = bars, start_idx, end_idx

        if self.timeframe not in timeframes:
            timeframes = (*timeframes, self.timeframe)

        def _on_range_change(bars_before: float, bars_after: float) -> None:
            bars, start_idx, end_idx = state["bars"], state["start_idx"], state["end_idx"]
            new_start, new_end = start_idx, end_idx
            if bars_before < edge_margin and start_idx > 0:
                new_start = max(0, start_idx - fetch_chunk)
            if bars_after < edge_margin and end_idx < bars.height:
                new_end = min(bars.height, end_idx + fetch_chunk)
            if (new_start, new_end) != (start_idx, end_idx):
                _render(bars, new_start, new_end)

        def _on_timeframe(new_timeframe: str) -> None:
            if new_timeframe == state["timeframe"]:
                return
            new_bars = resample(engine.base_1s, new_timeframe)
            # Anchor the new window on the same real-world instant that was at
            # the right edge before switching -- never past it, so the switch
            # can't reveal bars "later" than what was already being viewed.
            anchor_time = state["bars"]["timestamp"][state["end_idx"] - 1]
            end_idx = int((new_bars["timestamp"] <= anchor_time).sum())
            start_idx = max(0, end_idx - initial_bars)
            state["timeframe"] = new_timeframe
            _render(new_bars, start_idx, end_idx)

        bars0 = resample(engine.base_1s, self.timeframe)
        end_idx0 = bars0.height
        start_idx0 = max(0, end_idx0 - initial_bars)
        # Deliberately NOT wrapped in an outer chart.batch(): plot() (called
        # inside _render) already handles its own marker-series timing in two
        # phases internally, and wrapping it in an outer batch would make it
        # reentrant-collapse back into one send and defeat that (confirmed by
        # direct testing -- it also silently prevented the topbar switcher
        # created right after from ever appearing, since an earlier statement
        # throwing aborts every later statement in the same combined script).
        # Calling these sequentially after plot() has fully returned is what
        # keeps them safe.
        _render(bars0, start_idx0, end_idx0)
        state["timeframe"] = self.timeframe
        chart.on_range_change(_on_range_change)
        chart.add_timeframe_switcher(timeframes, default=self.timeframe, callback=_on_timeframe)

        return chart


class Engine:
    """Runs a `Strategy` over resampled bars and produces a trade log (spec §2.1).

    Loading is a separate concern — `Engine` is handed frames that were already
    cleaned upstream (`data.load_1s_data` / `data.resample`), and re-checks the
    1s base at construction so a dirty frame fails loudly here rather than
    silently corrupting a backtest.

    `backtest`: rising-edge entries honour the t+1 rule (§0.1) and spread-correct
    fills (§0.3). Each trade's exit is then resolved on the real 1s path
    (`_resolve_exit`, §2.3): SL / TP first-touch, an opposite-signal exit raced
    against them (only if `strategy.exit_on_opposite_signal`), or a force-close
    at end of data (§2.4). If `strategy.reverse_on_opposite_signal`, an
    opposite-signal exit immediately opens the opposite position at the same
    open — the chain continues until a trade exits via SL/TP/end-of-data.
    Scanning then resumes at the first signal bar at/after that exit, so trades
    never overlap in wall-clock time.
    """

    _TRADE_SCHEMA_TAIL = {
        "entry_price": pl.Float64,
        "direction": pl.String,
        "exit_price": pl.Float64,
        "pips": pl.Float64,
        "exit_reason": pl.String,
        "spread_pips_paid": pl.Float64,
    }
    _TRADE_COLUMNS = (
        "entry_time", "entry_price", "direction",
        "exit_time", "exit_price", "pips", "exit_reason", "spread_pips_paid",
    )

    def __init__(self, signal_df: pl.DataFrame, base_1s: pl.DataFrame) -> None:
        # Validate base_1s with the data layer's single source of truth
        # (spec §2.1) — never re-implement the §0.5 checks here.
        validate_1s(base_1s)
        self.base_1s = base_1s

        missing = [
            c for c in ("timestamp", "close_time", *_PRICE_COLUMNS)
            if c not in signal_df.columns
        ]
        if missing:
            raise ValueError(f"signal_df is missing column(s): {missing}")
        if not signal_df["timestamp"].is_sorted():
            raise ValueError("signal_df must be sorted by timestamp")
        self.signal_df = signal_df

        # Cache the 1s path as plain arrays once — the per-trade walk needs
        # contiguous numpy, and rebuilding it per trade would dominate runtime.
        self._ts_ns = base_1s["timestamp"].dt.epoch("ns").to_numpy()
        self._bid_high = base_1s["bid_high"].to_numpy()
        self._bid_low = base_1s["bid_low"].to_numpy()
        self._bid_close = base_1s["bid_close"].to_numpy()
        self._ask_high = base_1s["ask_high"].to_numpy()
        self._ask_low = base_1s["ask_low"].to_numpy()
        self._ask_close = base_1s["ask_close"].to_numpy()

    def backtest(self, strategy: Strategy) -> pl.DataFrame:
        """Run `strategy`; return the trade log.

        Columns: entry_time, entry_price, direction ("long"/"short"), exit_time,
        exit_price, pips, exit_reason in {"sl", "tp", "opposite_signal",
        "end_of_data"}, spread_pips_paid (half-spread in + half-spread out, pips —
        so gross = net pips + spread_pips_paid).
        """
        sig = strategy.generate_signals(self.signal_df)
        for col in ("long_signal", "short_signal"):
            if col not in sig.columns:
                raise ValueError(f"generate_signals did not add a {col!r} column")
            if sig.schema[col] != pl.Boolean:
                raise ValueError(
                    f"{col} must be pl.Boolean dtype, got {sig.schema[col]} (spec §0.4)"
                )
        if (sig["long_signal"] & sig["short_signal"]).any():
            raise ValueError("ambiguous bar: long_signal and short_signal both True")

        # Rising edges only — enter on a fresh False->True transition, not on
        # every bar a state signal stays True. shift(1, fill_value=False) keeps a
        # genuine Boolean dtype; `~` is a real logical-not here (spec §0.4).
        sig = sig.with_columns(
            _entry_long=pl.col("long_signal") & ~pl.col("long_signal").shift(1, fill_value=False),
            _entry_short=pl.col("short_signal") & ~pl.col("short_signal").shift(1, fill_value=False),
        )

        sig_ts = sig["timestamp"].to_list()                       # for the log
        sig_ts_ns = sig["timestamp"].dt.epoch("ns").to_numpy()    # for searchsorted
        ask_open = sig["ask_open"].to_list()
        bid_open = sig["bid_open"].to_list()
        entry_long = sig["_entry_long"].to_list()
        entry_short = sig["_entry_short"].to_list()

        base_ts = self.base_1s["timestamp"]
        n_sig = sig.height
        n_base = len(self._ts_ns)

        def resolve(entry_bar: int, direction: int):
            """Resolve one trade opened at signal bar `entry_bar`'s open,
            direction +1/-1. Returns (trade, resume_t, reversal); `reversal` is
            (new_entry_bar, new_direction) iff the trade exited opposite_signal
            and the strategy reverses, else None."""
            entry_time = sig_ts[entry_bar]
            # long fills at ask, short at bid — for a fresh entry AND a reversal
            # (the close and the re-open are the same side of the book, §0.3).
            entry_price = ask_open[entry_bar] if direction == 1 else bid_open[entry_bar]
            entry_half_spread = (ask_open[entry_bar] - bid_open[entry_bar]) / 2 / PIP
            sl_level, tp_level = _sl_tp_levels(
                direction, entry_price, strategy.sl_pips, strategy.tp_pips
            )

            # First 1s row at/after entry — the entry second is exposed to its
            # own range (open first, then the range unfolds, §0.2).
            start_idx = int(np.searchsorted(self._ts_ns, sig_ts_ns[entry_bar], side="left"))
            if direction == 1:                       # long exits by selling -> bid
                exit_high, exit_low = self._bid_high, self._bid_low
            else:                                    # short exits by buying -> ask
                exit_high, exit_low = self._ask_high, self._ask_low

            # Opposite-signal exit (spec §2.2) — race it against SL/TP. First
            # opposite rising edge at bar k >= entry_bar, acted on at k+1's open.
            end_idx = n_base
            signal_exit = None
            opp_bar = None
            if strategy.exit_on_opposite_signal:
                opp_edge = entry_short if direction == 1 else entry_long
                k = entry_bar
                while k < n_sig and not opp_edge[k]:
                    k += 1
                if k < n_sig and k + 1 < n_sig:
                    # Walk only up to (not including) bar k+1's open: the signal
                    # exit fills at that open, BEFORE the bar's range unfolds, so
                    # the position never sees k+1's intrabar SL/TP (§0.2).
                    end_idx = int(np.searchsorted(self._ts_ns, sig_ts_ns[k + 1], side="left"))
                    signal_exit = (
                        sig_ts[k + 1],
                        bid_open[k + 1] if direction == 1 else ask_open[k + 1],
                        int(sig_ts_ns[k + 1]),
                    )
                    opp_bar = k

            hit_idx, exit_price, reason = _resolve_exit(
                exit_high, exit_low, start_idx, end_idx, direction, sl_level, tp_level
            )

            if reason == _HIT_SL:  # SL genuinely happened first
                exit_time, exit_ns, exit_reason = base_ts[hit_idx], int(self._ts_ns[hit_idx]), "sl"
                exit_price = float(exit_price)
            elif reason == _HIT_TP:
                exit_time, exit_ns, exit_reason = base_ts[hit_idx], int(self._ts_ns[hit_idx]), "tp"
                exit_price = float(exit_price)
            elif signal_exit is not None:  # nothing touched first -> signal wins
                exit_time, exit_price, exit_ns = signal_exit[0], float(signal_exit[1]), signal_exit[2]
                exit_reason = "opposite_signal"
            else:  # _NO_TOUCH, no signal exit -> force close at end of data (§2.4)
                exit_time = base_ts[n_base - 1]
                exit_price = float(self._bid_close[-1] if direction == 1 else self._ask_close[-1])
                exit_ns, exit_reason = int(self._ts_ns[n_base - 1]), "end_of_data"

            if direction == 1:
                pips = (exit_price - entry_price) / PIP
            else:
                pips = (entry_price - exit_price) / PIP

            # Half-spread paid getting out, at the exit instant (spec §3.2 needs
            # the round-trip spread cost; entry-at-ask/exit-at-bid already bakes
            # it into `pips`, so gross = net + spread_pips_paid).
            if exit_reason in ("sl", "tp"):
                exit_half_spread = (self._ask_close[hit_idx] - self._bid_close[hit_idx]) / 2 / PIP
            elif exit_reason == "opposite_signal":
                exit_half_spread = (ask_open[opp_bar + 1] - bid_open[opp_bar + 1]) / 2 / PIP
            else:  # end_of_data
                exit_half_spread = (self._ask_close[-1] - self._bid_close[-1]) / 2 / PIP

            trade = {
                "entry_time": entry_time,
                "entry_price": float(entry_price),
                "direction": "long" if direction == 1 else "short",
                "exit_time": exit_time,
                "exit_price": exit_price,
                "pips": float(pips),
                "exit_reason": exit_reason,
                "spread_pips_paid": float(entry_half_spread + exit_half_spread),
            }

            resume_t = int(np.searchsorted(sig_ts_ns, exit_ns, side="left"))
            reversal = None
            if exit_reason == "opposite_signal" and strategy.reverse_on_opposite_signal:
                # re-open the opposite at the same bar/open we just closed at.
                # opp_bar strictly increases down the chain, so it terminates.
                reversal = (opp_bar + 1, -direction)
            return trade, resume_t, reversal

        trades: list[dict] = []
        t = 0
        # Small outer loop over the resampled frame — not the bottleneck (§2.3).
        while t < n_sig:
            if entry_long[t] and t + 1 < n_sig:
                direction = 1
            elif entry_short[t] and t + 1 < n_sig:
                direction = -1
            else:
                t += 1
                continue

            entry_bar = t + 1                        # acted on at t+1's open (§0.1)
            while True:
                trade, resume_t, reversal = resolve(entry_bar, direction)
                trades.append(trade)
                if reversal is None:
                    # Resume at the first signal bar at/after this exit — no
                    # wall-clock overlap, mid-hold edges skipped. max(t+1, …)
                    # guarantees progress.
                    t = max(t + 1, resume_t)
                    break
                entry_bar, direction = reversal      # keep flipping while opposite exits

        ts_dtype = self.base_1s["timestamp"].dtype
        return pl.DataFrame(
            trades,
            schema={
                "entry_time": ts_dtype,
                "exit_time": ts_dtype,
                **self._TRADE_SCHEMA_TAIL,
            },
        ).select(*self._TRADE_COLUMNS)

    def evaluate(
        self,
        trades: pl.DataFrame,
        *,
        starting_balance: float = 10_000.0,
        pip_value: float = 1.0,
        seed: int | None = None,
        **kw,
    ) -> dict:
        """Full performance report for a `backtest` trade log (spec §2.1 / §3).

        Thin orchestration over `lib.evaluate` — `evaluate` (§3.1) plus the four
        §3.2 checks (`adversarial`, `bootstrap_ci`, `mc_drawdown`). `seed` is
        passed to the resampling ones for reproducibility; extra kwargs
        (`exclude_best_pct`, `min_trades`, `n_resamples`, `n_shuffles`,
        `confidence`) are routed to whichever function accepts them.

        Returns::

            {"summary", "equity_curve", "monthly",   # from evaluate()
             "adversarial": {"gross_vs_net", "ex_best_month", "ex_best_trades",
                             "sample_size", "bootstrap_ci", "mc_drawdown"},
             "verdict": str}                          # sample-size-gated
        """
        from lib import evaluate as ev

        money = dict(starting_balance=starting_balance, pip_value=pip_value)
        adv = ev.adversarial(
            trades, **money,
            **{k: kw[k] for k in ("exclude_best_pct", "min_trades") if k in kw},
        )
        adv["bootstrap_ci"] = ev.bootstrap_ci(
            trades, seed=seed,
            **{k: kw[k] for k in ("n_resamples", "confidence") if k in kw},
        )
        adv["mc_drawdown"] = ev.mc_drawdown(
            trades, seed=seed, **money,
            **{k: kw[k] for k in ("n_shuffles",) if k in kw},
        )
        verdict = adv.pop("verdict")

        return {**ev.evaluate(trades, **money), "adversarial": adv, "verdict": verdict}