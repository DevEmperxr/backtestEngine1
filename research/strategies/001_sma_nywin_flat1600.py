"""001 — SMA 20/50 crossover, NY-open window, flat at London close.

See research/runs/001_sma_nywin_flat1600/summary.md for the pre-registered
hypothesis. 002 and 003 subclass this file's class and change only their
pre-registered parameters, so the signal logic is literally shared.
"""

from __future__ import annotations

from datetime import time

import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from lib.signals import atr, crossover, session_window, sma

NY, LONDON = "America/New_York", "Europe/London"
WINDOW_START = time(7, 0)    # 1h before the 08:00 New York FX open
WINDOW_END = time(16, 0)     # London close


class SmaNyWindowStrategy(Strategy):
    line_columns = ["sma_fast", "sma_slow"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    exit_on_opposite_signal = False   # user spec: no exit on opposite signal
    reverse_on_opposite_signal = False

    def __init__(
        self, *, fast_n: int = 20, slow_n: int = 50, sl_pips: float = 10.0,
        tp_pips: float = 15.0, timeframe: str = "5m", force_flat: bool = True,
        atr_sl_mult: float | None = None, atr_n: int = 14,
    ) -> None:
        super().__init__(sl_pips, tp_pips, timeframe)
        if not 1 <= fast_n < slow_n:
            raise ValueError(f"need 1 <= fast_n < slow_n, got {fast_n}, {slow_n}")
        self.fast_n, self.slow_n = fast_n, slow_n
        self.force_flat = force_flat
        # ATR mode: SL = atr_sl_mult * ATR at the signal bar, TP keeps the same
        # R multiple as the fixed tp_pips/sl_pips pair (15/10 = 1.5R).
        self.atr_sl_mult, self.atr_n = atr_sl_mult, atr_n

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        cross_up, cross_down = crossover(pl.col("sma_fast"), pl.col("sma_slow"))

        # Entry happens at the next bar's open == this bar's close_time, so the
        # window is judged on close_time: known at bar t's close, no lookahead.
        in_window = (
            session_window(pl.col("close_time"), NY, WINDOW_START, LONDON, WINDOW_END)
            & (pl.col("close_time").dt.convert_time_zone(NY).dt.weekday() <= 5)
        )

        out = df.with_columns(
            mid_close=mid("close"),
            in_window=in_window,
        ).with_columns(
            sma_fast=sma(pl.col("mid_close"), self.fast_n),
            sma_slow=sma(pl.col("mid_close"), self.slow_n),
        ).with_columns(
            cross_up=cross_up,
            cross_down=cross_down,
        ).with_columns(
            long_signal=pl.col("cross_up") & pl.col("in_window"),
            short_signal=pl.col("cross_down") & pl.col("in_window"),
        )

        if self.force_flat:
            # level: any bar closing outside the window flattens at the next
            # open; the first such bar closes at 16:00 London -> exit at the
            # 16:00 bar's open.
            out = out.with_columns(exit_signal=~pl.col("in_window"))

        if self.atr_sl_mult is not None:
            r_multiple = self.tp_pips / self.sl_pips
            out = out.with_columns(
                atr_pips=atr(mid("high"), mid("low"), pl.col("mid_close"), self.atr_n) / PIP,
            ).with_columns(
                sl_pips=pl.col("atr_pips") * self.atr_sl_mult,
            ).with_columns(
                tp_pips=pl.col("sl_pips") * r_multiple,
            )
        return out


# the pre-registered 001 configuration
def make() -> SmaNyWindowStrategy:
    return SmaNyWindowStrategy(fast_n=20, slow_n=50, sl_pips=10, tp_pips=15, force_flat=True)
