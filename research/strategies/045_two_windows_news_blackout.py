"""045 — run 042 (Idea 1, two entry windows) with a +-1 h blackout around every red-news release
for the pair's currencies: no entries from 1 h before to 1 h after the release, and any open trade
is closed 1 h before it. Release times: research/regime/news.py red_news_times(); events without a
recoverable time block their whole New York day.

See research/runs/045_two_windows_news_blackout/summary.md.
"""

from __future__ import annotations

from datetime import timedelta
from importlib import import_module

import numpy as np
import polars as pl

from research.regime.news import red_news_times

_042 = import_module("research.strategies.042_idea1_two_windows")


class TwoWindowNewsBlackout(_042.TwoWindowSweepFade):
    def __init__(self, *, currencies: tuple[str, ...] = ("USD", "EUR"), blackout_min: int = 60, **kw) -> None:
        super().__init__(**kw)
        self.currencies = tuple(currencies)
        self.blackout_min = blackout_min
        times, days = red_news_times(list(currencies))
        self.event_ns = np.array([int(t.timestamp() * 1e9) for t in times], dtype=np.int64)
        self.whole_days = sorted(days)

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = super().generate_signals(df)
        # close_time of bar k = the moment an order placed on k is filled (k+1 open)
        t = out["close_time"].dt.epoch("ns").to_numpy()
        w = int(timedelta(minutes=self.blackout_min).total_seconds() * 1e9)
        i = np.searchsorted(self.event_ns, t - w, side="left")          # first event >= t - 1h
        nxt = np.where(i < len(self.event_ns), self.event_ns[np.minimum(i, len(self.event_ns) - 1)], np.iinfo(np.int64).max)
        near = nxt <= t + w                                              # some event in [t - 1h, t + 1h]
        whole = out["close_time"].dt.convert_time_zone("America/New_York").dt.date().is_in(self.whole_days)
        blk = pl.Series("news_blackout", near) | whole
        out = out.with_columns(blk)
        return out.with_columns(
            long_signal=pl.col("long_signal") & ~pl.col("news_blackout"),
            short_signal=pl.col("short_signal") & ~pl.col("news_blackout"),
            exit_signal=pl.col("exit_signal") | pl.col("news_blackout"),
        )


def make() -> TwoWindowNewsBlackout:
    base = _042.make()
    return TwoWindowNewsBlackout(**{k: getattr(base, k) for k in (
        "mode", "stretch_atr", "pivot_k", "er_trend", "timeframe", "stop_mode", "stop_atr_mult",
        "window_start", "window_start_tz", "window_end", "window_end_tz")})
