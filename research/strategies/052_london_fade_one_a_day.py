"""052 — the London fade (046) with at most ONE trade per New York day: only the first entry signal
of each NY calendar day is kept (after the news blackout). Every trade is closed by 16:00 NY, so
the first signal of a day always becomes that day's trade.

See research/runs/052_london_fade_one_a_day/summary.md.
"""

from __future__ import annotations

from importlib import import_module

import polars as pl

_046 = import_module("research.strategies.046_london_fade_standalone")
_m = import_module("research.strategies.022_sweep_fade_to_ma")


class LondonFadeOneADay(_046.LondonFade):
    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        sig = pl.col("long_signal") | pl.col("short_signal")
        day = pl.col("close_time").dt.convert_time_zone(_m.NY).dt.date()
        first = sig & (sig.cast(pl.Int32).cum_sum().over(day) == 1)   # causal: count so far today
        return out.with_columns(long_signal=pl.col("long_signal") & first,
                                short_signal=pl.col("short_signal") & first)


def make() -> LondonFadeOneADay:
    base = _046.make()
    return LondonFadeOneADay(**{k: getattr(base, k) for k in (
        "mode", "stretch_atr", "pivot_k", "er_trend", "timeframe", "stop_mode", "stop_atr_mult",
        "window_start", "window_start_tz", "window_end", "window_end_tz")})
