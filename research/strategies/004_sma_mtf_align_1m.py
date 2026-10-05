"""004 — 1m SMA 20/50 cross, only in the direction of the 5m AND 15m SMA 20/50
trend (last closed bars), NY-open window, flat at London close, SL 4 / TP 6.

See research/runs/004_sma_mtf_align_1m/summary.md for the pre-registered
hypothesis.
"""

from __future__ import annotations

from datetime import time

import polars as pl

from lib.engine import Strategy
from lib.signals import crossover, higher_tf_join, session_window, sma

NY, LONDON = "America/New_York", "Europe/London"
WINDOW_START = time(7, 0)
WINDOW_END = time(16, 0)


class SmaMtfAlignStrategy(Strategy):
    line_columns = ["sma_fast", "sma_slow"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False

    def __init__(
        self, *, fast_n: int = 20, slow_n: int = 50, sl_pips: float = 4.0,
        tp_pips: float = 6.0, timeframe: str = "1m",
        trend_timeframes: tuple[str, ...] = ("5m", "15m"), force_flat: bool = True,
    ) -> None:
        super().__init__(sl_pips, tp_pips, timeframe)
        if not 1 <= fast_n < slow_n:
            raise ValueError(f"need 1 <= fast_n < slow_n, got {fast_n}, {slow_n}")
        self.fast_n, self.slow_n = fast_n, slow_n
        self.trend_timeframes = tuple(trend_timeframes)
        self.force_flat = force_flat

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = df.with_columns(
            mid_close=(pl.col("bid_close") + pl.col("ask_close")) / 2,
            # entry is at the next bar's open == this bar's close_time
            in_window=(
                session_window(pl.col("close_time"), NY, WINDOW_START, LONDON, WINDOW_END)
                & (pl.col("close_time").dt.convert_time_zone(NY).dt.weekday() <= 5)
            ),
        ).with_columns(
            sma_fast=sma(pl.col("mid_close"), self.fast_n),
            sma_slow=sma(pl.col("mid_close"), self.slow_n),
        )
        cross_up, cross_down = crossover(pl.col("sma_fast"), pl.col("sma_slow"))
        out = out.with_columns(cross_up=cross_up, cross_down=cross_down)

        # Higher-timeframe trend from the LAST CLOSED bar only (as-of backward on
        # close_time inside higher_tf_join) — a forming 5m/15m bar is invisible.
        up_all, down_all = pl.lit(True), pl.lit(True)
        for tf in self.trend_timeframes:
            diff = sma(pl.col("close"), self.fast_n) - sma(pl.col("close"), self.slow_n)
            out = higher_tf_join(out, tf, "mid_close", {f"trend_{tf}": diff})
            up_all = up_all & (pl.col(f"trend_{tf}") > 0).fill_null(False)
            down_all = down_all & (pl.col(f"trend_{tf}") < 0).fill_null(False)

        out = out.with_columns(
            long_signal=pl.col("cross_up") & up_all & pl.col("in_window"),
            short_signal=pl.col("cross_down") & down_all & pl.col("in_window"),
        )
        if self.force_flat:
            out = out.with_columns(exit_signal=~pl.col("in_window"))
        return out


def make() -> SmaMtfAlignStrategy:
    return SmaMtfAlignStrategy(
        fast_n=20, slow_n=50, sl_pips=4, tp_pips=6, timeframe="1m",
        trend_timeframes=("5m", "15m"), force_flat=True,
    )
