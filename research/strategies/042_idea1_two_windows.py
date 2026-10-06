"""042 — Idea 1 (023A rules) with entries only in two windows:
  * 03:00–04:59 New York (first 2 h after the London open) AND 1h sideways   (London fade)
  * 08:00–09:59 New York AND 1h trending, trade with the trend            (NY open window)
Window 08:00 London -> 16:00 NY, flat 16:00 NY, one position at a time.
See research/runs/042_idea1_two_windows/summary.md.
"""

from __future__ import annotations

from datetime import time
from importlib import import_module

import polars as pl

_m = import_module("research.strategies.022_sweep_fade_to_ma")


class TwoWindowSweepFade(_m.SweepFadeStrategy):
    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        hr = pl.col("close_time").dt.convert_time_zone("America/New_York").dt.hour()
        keep = ((hr.is_in([3, 4]) & (pl.col("ctx_class") == "sideways"))
                | (hr.is_in([8, 9]) & (pl.col("ctx_class") == "trend_with"))).fill_null(False)
        return out.with_columns(
            window_tag=pl.when(hr.is_in([3, 4])).then(pl.lit("london_sideways")).otherwise(pl.lit("ny_trend")),
            long_signal=pl.col("long_signal") & keep,
            short_signal=pl.col("short_signal") & keep,
        )


def make() -> TwoWindowSweepFade:
    return TwoWindowSweepFade(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                              timeframe="1m", stop_mode="atr", stop_atr_mult=1.5,
                              window_start=time(8, 0), window_start_tz=_m.LONDON,
                              window_end=time(16, 0), window_end_tz=_m.NY)
