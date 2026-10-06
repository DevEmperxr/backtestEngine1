"""049 — the London fade with the 048 stop (sweep candle + 3 pips), target 4R instead of the 5m SMA20,
and the stop moved to break-even once price has moved +2R in favour (R = the stop distance).
Entry rules, hours, context, flat 16:00 NY and the news blackout as 046.

See research/runs/049_london_fade_be2r_tp4r/summary.md.
"""

from __future__ import annotations

from datetime import time
from importlib import import_module

import polars as pl

_046 = import_module("research.strategies.046_london_fade_standalone")
_m = import_module("research.strategies.022_sweep_fade_to_ma")


class LondonFadeRunner(_046.LondonFade):
    def __init__(self, *, tp_r: float = 4.0, be_r: float = 2.0, **kw) -> None:
        super().__init__(**kw)
        self.tp_r, self.be_r = tp_r, be_r
        self.be_frac = be_r / tp_r          # lets the run_experiment audit check break-even exits

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        sig = pl.col("long_signal") | pl.col("short_signal")
        return out.with_columns(
            tp_pips=pl.when(sig).then(self.tp_r * pl.col("sl_pips")),
            be_trigger_pips=pl.when(sig).then(self.be_r * pl.col("sl_pips")),
        )


def make() -> LondonFadeRunner:
    return LondonFadeRunner(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                            timeframe="1m", stop_mode="sweep", stop_buffer_pips=3.0,
                            window_start=time(8, 0), window_start_tz=_m.LONDON,
                            window_end=time(16, 0), window_end_tz=_m.NY)
