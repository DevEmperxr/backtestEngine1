"""078 — PIPELINE CHECK for index CFDs (not a research strategy): long at 09:35 New York, flat at 15:55 New York,
100-point stop, no target. Used once to confirm that points, spreads, the FTMO spread top-up, the US news filter and the
lookahead audit all work end to end on NAS100. Its result is not evidence of anything.
"""

from __future__ import annotations

from datetime import time

import polars as pl

from lib.engine import Strategy
from research.regime.news import apply_news_blackout

NY = "America/New_York"


class IndexPipelineCheck(Strategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    pip_aware = True

    def __init__(self, *, currencies: tuple[str, ...] = ("USD",)) -> None:
        super().__init__(100.0, 1000.0, "1m")
        self.currencies = tuple(currencies)

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        ny = pl.col("close_time").dt.convert_time_zone(NY)
        clock = ny.dt.time()
        wd = ny.dt.weekday() <= 5
        out = df.with_columns(
            long_signal=((clock == time(9, 35)) & wd).fill_null(False),
            short_signal=pl.lit(False),
            in_window=((clock >= time(9, 35)) & (clock < time(15, 55)) & wd).fill_null(False),
        )
        out = out.with_columns(exit_signal=~pl.col("in_window") & ~pl.col("long_signal"))
        return apply_news_blackout(out, list(self.currencies))


def make():
    return IndexPipelineCheck()
