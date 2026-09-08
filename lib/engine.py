"""Backtest engine (spec §2).

Contains the `Strategy` ABC (§2.2) and `Engine` (§2.1), plus the numba 1s-path
SL/TP resolver (`_resolve_exit`, §2.3). `Engine` is being built in passes:

    5a  — construction + entry timing (done). Exits are a crude placeholder.
    5b  — `_resolve_exit` (this file) + wiring it into `backtest` with
          `exit_on_opposite_signal`. Part 1 here is the standalone resolver.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import polars as pl
from numba import njit

from lib.data import PIP, validate_1s

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
    """

    exit_on_opposite_signal: bool = True

    def __init__(self, sl_pips: float, tp_pips: float, timeframe: str) -> None:
        if not (sl_pips > 0):
            raise ValueError(f"sl_pips must be > 0, got {sl_pips!r}")
        if not (tp_pips > 0):
            raise ValueError(f"tp_pips must be > 0, got {tp_pips!r}")
        if not isinstance(timeframe, str) or not timeframe:
            raise ValueError(f"timeframe must be a non-empty str, got {timeframe!r}")
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


class Engine:
    """Runs a `Strategy` over resampled bars and produces a trade log (spec §2.1).

    Loading is a separate concern — `Engine` is handed frames that were already
    cleaned upstream (`data.load_1s_data` / `data.resample`), and re-checks the
    1s base at construction so a dirty frame fails loudly here rather than
    silently corrupting a backtest.

    Pass 5a scope: entry timing only. `backtest` honours the t+1 rule (§0.1) and
    spread-correct fills (§0.3), one position at a time. Exits are a placeholder
    — a position is closed at the next opposite signal's t+1 open. Pass 5b
    replaces that with the SL/TP 1s-path walk and `exit_on_opposite_signal`.
    """

    _TRADE_COLUMNS = ("entry_time", "entry_price", "direction", "exit_time", "exit_price")

    def __init__(self, signal_df: pl.DataFrame, base_1s: pl.DataFrame) -> None:
        # base_1s: the 1s base frame. Needed for 5b's fill walk; just held now.
        # Validate with the data layer's single source of truth (spec §2.1) —
        # never re-implement the §0.5 checks here.
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

    def backtest(self, strategy: Strategy) -> pl.DataFrame:
        """Run `strategy` and return the entry log (5a: entries + placeholder exits)."""
        sig = strategy.generate_signals(self.signal_df)
        for col in ("long_signal", "short_signal"):
            if col not in sig.columns:
                raise ValueError(f"generate_signals did not add a {col!r} column")
            if sig.schema[col] != pl.Boolean:
                raise ValueError(
                    f"{col} must be pl.Boolean dtype, got {sig.schema[col]} (spec §0.4)"
                )

        # t+1 timing (spec §0.1): a signal on bar t is actionable at bar t+1's
        # open. shift(1, fill_value=False) keeps a genuine Boolean dtype — the
        # §0.4 discipline, even though polars doesn't have pandas' object-upcast.
        sig = sig.with_columns(
            _act_long=pl.col("long_signal").shift(1, fill_value=False),
            _act_short=pl.col("short_signal").shift(1, fill_value=False),
        )

        ts = sig["timestamp"].to_list()
        ask_open = sig["ask_open"].to_list()
        bid_open = sig["bid_open"].to_list()
        act_long = sig["_act_long"].to_list()
        act_short = sig["_act_short"].to_list()

        trades: list[dict] = []
        direction: str | None = None
        entry_time = None
        entry_price = None

        # Small outer loop over the resampled frame — not the bottleneck (§2.3).
        for i in range(sig.height):
            if direction is None:
                if act_long[i]:
                    direction, entry_time, entry_price = "long", ts[i], ask_open[i]
                elif act_short[i]:
                    direction, entry_time, entry_price = "short", ts[i], bid_open[i]
            elif direction == "long" and act_short[i]:
                # placeholder exit: closing a long is a sell -> fills at bid.
                trades.append({
                    "entry_time": entry_time, "entry_price": entry_price,
                    "direction": "long",
                    "exit_time": ts[i], "exit_price": bid_open[i],
                })
                direction = entry_time = entry_price = None
            elif direction == "short" and act_long[i]:
                # closing a short is a buy -> fills at ask.
                trades.append({
                    "entry_time": entry_time, "entry_price": entry_price,
                    "direction": "short",
                    "exit_time": ts[i], "exit_price": ask_open[i],
                })
                direction = entry_time = entry_price = None
            # same-direction signal while in a position: ignored (one at a time).

        if direction is not None:
            # still open at end of data — keep it, exit unresolved in 5a.
            trades.append({
                "entry_time": entry_time, "entry_price": entry_price,
                "direction": direction, "exit_time": None, "exit_price": None,
            })

        ts_dtype = self.signal_df["timestamp"].dtype
        return pl.DataFrame(
            trades,
            schema={
                "entry_time": ts_dtype,
                "entry_price": pl.Float64,
                "direction": pl.String,
                "exit_time": ts_dtype,
                "exit_price": pl.Float64,
            },
        )