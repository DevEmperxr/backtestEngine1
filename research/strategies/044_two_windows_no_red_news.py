"""044 — run 042 (Idea 1, two entry windows: London-open sideways + NY-open trending) with no
entries on red-news days for the pair's currencies (ForexFactory High Impact, research/regime/news.py).

See research/runs/044_two_windows_no_red_news/summary.md.
"""

from __future__ import annotations

from importlib import import_module

import polars as pl

from research.regime.news import red_news_dates

_042 = import_module("research.strategies.042_idea1_two_windows")


class TwoWindowNoRedNews(_042.TwoWindowSweepFade):
    def __init__(self, *, currencies: tuple[str, ...] = ("USD", "EUR"), **kw) -> None:
        super().__init__(**kw)
        self.currencies = tuple(currencies)
        self.red_dates = sorted(red_news_dates(list(currencies)))

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        red = pl.col("close_time").dt.convert_time_zone("America/New_York").dt.date().is_in(self.red_dates)
        return out.with_columns(
            red_day=red,
            long_signal=pl.col("long_signal") & ~red,
            short_signal=pl.col("short_signal") & ~red,
        )


def make() -> TwoWindowNoRedNews:
    base = _042.make()
    return TwoWindowNoRedNews(**{k: getattr(base, k) for k in (
        "mode", "stretch_atr", "pivot_k", "er_trend", "timeframe", "stop_mode", "stop_atr_mult",
        "window_start", "window_start_tz", "window_end", "window_end_tz")})
