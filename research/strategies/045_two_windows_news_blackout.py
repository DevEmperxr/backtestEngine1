"""045 — run 042 (Idea 1, two entry windows) with a +-1 h blackout around every red-news release
for the pair's currencies: no entries from 1 h before to 1 h after the release, and any open trade
is closed 1 h before it. Release times: research/regime/news.py red_news_times(); events without a
recoverable time block their whole New York day.

See research/runs/045_two_windows_news_blackout/summary.md.
"""

from __future__ import annotations

from importlib import import_module

import polars as pl

from research.regime.news import apply_news_blackout

_042 = import_module("research.strategies.042_idea1_two_windows")


class TwoWindowNewsBlackout(_042.TwoWindowSweepFade):
    def __init__(self, *, currencies: tuple[str, ...] = ("USD", "EUR"), blackout_min: int = 60, **kw) -> None:
        super().__init__(**kw)
        self.currencies = tuple(currencies)
        self.blackout_min = blackout_min

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        return apply_news_blackout(super().generate_signals(df), list(self.currencies), self.blackout_min)


def make() -> TwoWindowNewsBlackout:
    base = _042.make()
    return TwoWindowNewsBlackout(**{k: getattr(base, k) for k in (
        "mode", "stretch_atr", "pivot_k", "er_trend", "timeframe", "stop_mode", "stop_atr_mult",
        "window_start", "window_start_tz", "window_end", "window_end_tz")})
