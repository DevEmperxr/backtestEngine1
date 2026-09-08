"""Backtest engine (spec §2).

This module currently holds only the `Strategy` abstract base class (§2.2). The
`Engine` itself lands in a follow-up task.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import polars as pl


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