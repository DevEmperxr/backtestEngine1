"""029 — Idea 2 (025, targets B and C) with no entries on red-news days for the pair's
currencies (ForexFactory High Impact, see research/regime/news.py).

See research/runs/029_idea2_no_red_news/summary.md.
"""

from __future__ import annotations

from importlib import import_module

import polars as pl

from research.regime.news import red_news_dates

_025 = import_module("research.strategies.025_turn_confirm_continuation")


class NoRedNewsTurnStrategy(_025.TurnConfirmStrategy):
    def __init__(self, *, currencies: tuple[str, ...] = ("USD", "EUR"), **kw) -> None:
        super().__init__(**kw)
        self.currencies = tuple(currencies)
        self.red_dates = sorted(red_news_dates(list(currencies)))

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        ny_day = pl.col("close_time").dt.convert_time_zone("America/New_York").dt.date()
        red = ny_day.is_in(self.red_dates)
        return out.with_columns(
            red_day=red,
            long_signal=pl.col("long_signal") & ~red,
            short_signal=pl.col("short_signal") & ~red,
        )


def make_b() -> NoRedNewsTurnStrategy:
    return NoRedNewsTurnStrategy(target="2r")


def make_c() -> NoRedNewsTurnStrategy:
    return NoRedNewsTurnStrategy(target="swing1h")


make = make_b
