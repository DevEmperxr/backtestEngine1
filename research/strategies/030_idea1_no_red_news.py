"""030 — Idea 1 (023A) with no entries on red-news days for the pair's currencies
(ForexFactory High Impact, see research/regime/news.py).

See research/runs/030_idea1_no_red_news/summary.md.
"""

from __future__ import annotations

from importlib import import_module

import polars as pl

from research.regime.news import red_news_dates

_022 = import_module("research.strategies.022_sweep_fade_to_ma")


class NoRedNewsSweepFade(_022.SweepFadeStrategy):
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


def make() -> NoRedNewsSweepFade:
    return NoRedNewsSweepFade(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32,
                              timeframe="1m", stop_mode="atr", stop_atr_mult=1.5)
