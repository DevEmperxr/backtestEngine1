"""077 — Asian-session trades (19:00 -> 03:00 New York): gold long in a daily uptrend, AUDUSD with the daily trend,
plus "always long" references. Pip-aware. See research/runs/077_asia_session/summary.md.

    make_gold_trend()  make_gold_always()  make_aud_trend()  make_aud_always()
"""

from __future__ import annotations

from datetime import time, timedelta
from pathlib import Path

import polars as pl

from lib.data import pip_size
from lib.engine import Strategy
from research.regime.news import apply_news_blackout

NY = "America/New_York"
DERIVED = Path(__file__).resolve().parents[2] / "data" / "derived"


class AsiaSession(Strategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    pip_aware = True
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, *, pair: str, mode: str, stop_datr: float = 0.5) -> None:
        super().__init__(10.0, 10.0, "1m")
        if mode not in ("trend_long_only", "trend_both", "always_long"):
            raise ValueError(mode)
        self.pair, self.mode, self.stop_datr = pair, mode, stop_datr
        self.currencies = (pair[:3], pair[3:])
        self.pip = pip_size(pair)

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        ny = pl.col("close_time").dt.convert_time_zone(NY)
        out = df.with_columns(fxday=(pl.col("timestamp").dt.convert_time_zone(NY) + timedelta(hours=7)).dt.date())
        d = (pl.read_parquet(DERIVED / f"{self.pair.lower()}_daily_2023_2024.parquet").sort("fxday")
             .with_columns(datr_prev=pl.col("datr").shift(1)).select("fxday", "trend_prev", "datr_prev"))
        out = out.join(d, on="fxday", how="left")
        clock = ny.dt.time()
        fx_wd = pl.col("fxday").dt.weekday() <= 5
        at_entry = (clock == time(19, 0)) & fx_wd & pl.col("datr_prev").is_not_null()
        if self.mode == "always_long":
            long_, short = at_entry, pl.lit(False)
        elif self.mode == "trend_long_only":
            long_, short = at_entry & (pl.col("trend_prev") == 1), pl.lit(False)
        else:
            long_, short = at_entry & (pl.col("trend_prev") == 1), at_entry & (pl.col("trend_prev") == -1)
        in_win = ((clock >= time(19, 0)) | (clock < time(3, 0))) & fx_wd
        out = out.with_columns(long_signal=long_.fill_null(False), short_signal=short.fill_null(False),
                               in_window=in_win.fill_null(False))
        sig = pl.col("long_signal") | pl.col("short_signal")
        dist = self.stop_datr * pl.col("datr_prev") / self.pip
        out = out.with_columns(sl_pips=pl.when(sig).then(dist), tp_pips=pl.when(sig).then(10 * dist),
                               exit_signal=~pl.col("in_window") & ~sig)
        return apply_news_blackout(out, list(self.currencies))


def make_gold_trend():  return AsiaSession(pair="XAUUSD", mode="trend_long_only")   # noqa: E704
def make_gold_always(): return AsiaSession(pair="XAUUSD", mode="always_long")       # noqa: E704
def make_aud_trend():   return AsiaSession(pair="AUDUSD", mode="trend_both")        # noqa: E704
def make_aud_always():  return AsiaSession(pair="AUDUSD", mode="always_long")       # noqa: E704
