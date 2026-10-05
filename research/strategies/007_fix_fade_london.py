"""007 — Fade EURUSD's 15:00->16:00 London move at the 16:00 London (WM/R) fix,
hold to 16:00 New York (Krohn, Mueller & Whelan, JF 2024).

See research/runs/007_fix_fade_london/summary.md.
"""

from __future__ import annotations

from datetime import time

import polars as pl

from lib.engine import Strategy
from lib.signals import session_window

NY, LONDON = "America/New_York", "Europe/London"


class FixFadeStrategy(Strategy):
    line_columns = ["mid_close"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    force_flat = True
    audit_kind = "fix_fade"

    def __init__(
        self, *, fix_time: time = time(16, 0), lookback_min: int = 60,
        window_end: time = time(16, 0), window_end_tz: str = NY,
        sl_pips: float = 50.0, tp_pips: float = 50.0, timeframe: str = "1m",
    ) -> None:
        super().__init__(sl_pips, tp_pips, timeframe)
        self.fix_time, self.lookback_min = fix_time, lookback_min
        self.window_end, self.window_end_tz = window_end, window_end_tz

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        close_l = pl.col("close_time").dt.convert_time_zone(LONDON)
        out = df.with_columns(
            mid_close=(pl.col("bid_close") + pl.col("ask_close")) / 2,
            # holding window, judged on close_time (= next bar's open):
            # [16:00 London, 16:00 NY)
            in_window=session_window(pl.col("close_time"), LONDON, self.fix_time,
                                     self.window_end_tz, self.window_end)
                      & (close_l.dt.weekday() <= 5),
            is_fix_bar=(close_l.dt.time() == self.fix_time) & (close_l.dt.weekday() <= 5),
        )
        # mid close exactly lookback_min earlier, looked up by time (not by row
        # offset) so a missing bar can never silently shift the window
        past = out.select(
            pl.col("close_time").dt.offset_by(f"{self.lookback_min}m").alias("close_time"),
            pl.col("mid_close").alias("mid_close_lb"),
        )
        out = out.join(past, on="close_time", how="left", maintain_order="left").with_columns(
            r_lookback=pl.col("mid_close") - pl.col("mid_close_lb"),
        )
        out = out.with_columns(
            long_signal=(pl.col("is_fix_bar") & (pl.col("r_lookback") < 0)).fill_null(False),
            short_signal=(pl.col("is_fix_bar") & (pl.col("r_lookback") > 0)).fill_null(False),
            exit_signal=~pl.col("in_window"),
        )
        return out

    @staticmethod
    def report_splits(trades: pl.DataFrame, sig: pl.DataFrame) -> dict[str, pl.DataFrame]:
        """Pre-registered descriptive split: |15:00->16:00 move| above vs at/below
        its median across traded days."""
        t = trades.join(sig.select(pl.col("close_time").alias("entry_time"), "r_lookback"),
                        on="entry_time", how="left")
        med = t["r_lookback"].abs().median()
        big = t["r_lookback"].abs() > med
        cols = trades.columns
        return {"big_prefix_move": t.filter(big).select(cols),
                "small_prefix_move": t.filter(~big).select(cols)}


def make() -> FixFadeStrategy:
    return FixFadeStrategy(fix_time=time(16, 0), lookback_min=60,
                           window_end=time(16, 0), window_end_tz=NY, sl_pips=50, tp_pips=50)
