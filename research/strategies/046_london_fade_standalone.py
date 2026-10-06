"""046 — the London-open sideways fade on its own: Idea 1 (023A rules), entries only 03:00–04:59
New York with the 1h sideways, window 08:00 London -> 16:00 NY (flat 16:00 NY), one position at a
time, with the standing +-1 h red-news blackout (research/regime/news.py apply_news_blackout).

See research/runs/046_london_fade_standalone/summary.md.
"""

from __future__ import annotations

from datetime import time
from importlib import import_module

import polars as pl

from research.regime.news import apply_news_blackout

_m = import_module("research.strategies.022_sweep_fade_to_ma")


class LondonFade(_m.SweepFadeStrategy):
    def __init__(self, *, currencies: tuple[str, ...] = ("USD", "EUR"), blackout_min: int = 60, **kw) -> None:
        super().__init__(**kw)
        self.currencies = tuple(currencies)
        self.blackout_min = blackout_min

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        hr = pl.col("close_time").dt.convert_time_zone("America/New_York").dt.hour()
        keep = (hr.is_in([3, 4]) & (pl.col("ctx_class") == "sideways")).fill_null(False)
        out = out.with_columns(
            window_tag=pl.lit("london_sideways"),
            long_signal=pl.col("long_signal") & keep,
            short_signal=pl.col("short_signal") & keep,
        )
        return apply_news_blackout(out, list(self.currencies), self.blackout_min)


def make() -> LondonFade:
    return LondonFade(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                      timeframe="1m", stop_mode="atr", stop_atr_mult=1.5,
                      window_start=time(8, 0), window_start_tz=_m.LONDON,
                      window_end=time(16, 0), window_end_tz=_m.NY)
