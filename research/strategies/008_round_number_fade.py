"""008 — Fade a 1m touch-and-reject of a 50-pip round number (Osler 2003),
inside 07:00 NY -> 16:00 London, SL 4 pips beyond the level, TP 1.5 x SL.

See research/runs/008_round_number_fade/summary.md.
"""

from __future__ import annotations

from datetime import time

import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from lib.signals import session_window

NY, LONDON = "America/New_York", "Europe/London"


class RoundNumberFadeStrategy(Strategy):
    line_columns = ["level"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    force_flat = True
    audit_kind = "round_number"

    def __init__(
        self, *, step_pips: int = 50, sl_beyond_pips: float = 4.0, tp_r: float = 1.5,
        timeframe: str = "1m",
    ) -> None:
        super().__init__(sl_beyond_pips, sl_beyond_pips * tp_r, timeframe)
        self.step_pips, self.sl_beyond_pips, self.tp_r = step_pips, sl_beyond_pips, tp_r
        self.window_end, self.window_end_tz = time(16, 0), LONDON

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        pips = lambda e: (e / PIP).round(4)          # pip units, float noise removed
        step = self.step_pips
        out = df.with_columns(
            o=pips(mid("open")), h=pips(mid("high")), l=pips(mid("low")), c=pips(mid("close")),
            mid_close=mid("close"),
            in_window=session_window(pl.col("close_time"), NY, time(7, 0), LONDON, time(16, 0))
                      & (pl.col("close_time").dt.convert_time_zone(NY).dt.weekday() <= 5),
        ).with_columns(
            lvl_above=(pl.col("o") / step).floor() * step + step,   # first level strictly above open
            lvl_below=(pl.col("o") / step).ceil() * step - step,    # first level strictly below open
        ).with_columns(
            # touched from one side and closed back: uses only bar t's own OHLC
            rej_up=(pl.col("h") >= pl.col("lvl_above")) & (pl.col("c") < pl.col("lvl_above")),
            rej_dn=(pl.col("l") <= pl.col("lvl_below")) & (pl.col("c") > pl.col("lvl_below")),
        ).with_columns(
            short_signal=pl.col("rej_up") & ~pl.col("rej_dn") & pl.col("in_window"),
            long_signal=pl.col("rej_dn") & ~pl.col("rej_up") & pl.col("in_window"),
        ).with_columns(
            level=pl.when(pl.col("short_signal")).then(pl.col("lvl_above") * PIP)
                   .when(pl.col("long_signal")).then(pl.col("lvl_below") * PIP),
            sl_pips=pl.when(pl.col("short_signal"))
                     .then(pl.col("lvl_above") + self.sl_beyond_pips - pl.col("c"))
                     .when(pl.col("long_signal"))
                     .then(pl.col("c") - (pl.col("lvl_below") - self.sl_beyond_pips)),
        ).with_columns(
            tp_pips=pl.col("sl_pips") * self.tp_r,
            exit_signal=~pl.col("in_window"),
        )
        return out.drop("o", "h", "l", "c")

    @staticmethod
    def report_splits(trades: pl.DataFrame, sig: pl.DataFrame) -> dict[str, pl.DataFrame]:
        """Pre-registered descriptive split: x.xx00 vs x.xx50 levels."""
        t = trades.join(sig.select(pl.col("close_time").alias("entry_time"), "level"),
                        on="entry_time", how="left")
        is00 = ((t["level"] / PIP).round(0) % 100) == 0
        cols = trades.columns
        return {"level_00": t.filter(is00).select(cols), "level_50": t.filter(~is00).select(cols)}


def make() -> RoundNumberFadeStrategy:
    return RoundNumberFadeStrategy(step_pips=50, sl_beyond_pips=4.0, tp_r=1.5)
