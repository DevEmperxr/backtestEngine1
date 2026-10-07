"""065 — fade a sweep of the Tokyo first-hour range (09:00–10:00 Tokyo) during the second hour (10:00–11:00 Tokyo).

Sweep: a 1m bar whose mid high goes above the first-hour high and closes back below it (sell), or the mirror at
the low (buy); first sweep of the day only. Entry next 1m open; stop = sweep extreme + 0.5 x first-hour range;
target = first-hour midpoint (skipped if already past it); flat 12:00 Tokyo. Standing ±1 h news blackout.

See research/runs/065_tokyo_second_hour_sweep/summary.md.
"""

from __future__ import annotations

from datetime import time

import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from research.regime.news import apply_news_blackout

TOKYO = "Asia/Tokyo"


class TokyoSweep(Strategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    line_columns = ["r_high", "r_low", "r_mid"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, *, currencies: tuple[str, ...] = ("AUD", "USD"), stop_range_mult: float = 0.5,
                 blackout_min: int = 60) -> None:
        super().__init__(10.0, 10.0, "1m")       # per-trade columns override these
        self.currencies, self.stop_range_mult, self.blackout_min = tuple(currencies), stop_range_mult, blackout_min

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        tk = pl.col("close_time").dt.convert_time_zone(TOKYO)
        tko = pl.col("timestamp").dt.convert_time_zone(TOKYO)
        out = df.with_columns(mh=mid("high"), ml=mid("low"), mc=mid("close"), tday=tk.dt.date(),
                              clock=tk.dt.time(), oclock=tko.dt.time(), wk=tk.dt.weekday() <= 5)
        first = (out.filter((pl.col("oclock") >= time(9, 0)) & (pl.col("oclock") < time(10, 0)) & pl.col("wk"))
                 .group_by("tday").agg(r_high=pl.col("mh").max(), r_low=pl.col("ml").min(), r_n=pl.len()))
        out = out.join(first.filter(pl.col("r_n") >= 50), on="tday", how="left").with_columns(
            r_mid=(pl.col("r_high") + pl.col("r_low")) / 2, r_rng=pl.col("r_high") - pl.col("r_low"))
        win = (pl.col("clock") > time(10, 0)) & (pl.col("clock") <= time(11, 0)) & pl.col("wk") & pl.col("r_high").is_not_null()
        sell = win & (pl.col("mh") > pl.col("r_high")) & (pl.col("mc") < pl.col("r_high")) & (pl.col("mc") > pl.col("r_mid"))
        buy = win & (pl.col("ml") < pl.col("r_low")) & (pl.col("mc") > pl.col("r_low")) & (pl.col("mc") < pl.col("r_mid"))
        any_ = sell | buy
        first_sig = any_ & (any_.cast(pl.Int32).cum_sum().over("tday") == 1)
        out = out.with_columns(
            short_signal=(first_sig & sell).fill_null(False),
            long_signal=(first_sig & buy).fill_null(False),
            in_window=((pl.col("clock") > time(10, 0)) & (pl.col("clock") <= time(12, 0)) & pl.col("wk")).fill_null(False),
        )
        k = self.stop_range_mult
        out = out.with_columns(
            sl_pips=pl.when(pl.col("short_signal")).then((pl.col("mh") + k * pl.col("r_rng") - pl.col("mc")) / PIP)
                      .when(pl.col("long_signal")).then((pl.col("mc") - (pl.col("ml") - k * pl.col("r_rng"))) / PIP),
            tp_pips=pl.when(pl.col("short_signal")).then((pl.col("mc") - pl.col("r_mid")) / PIP)
                      .when(pl.col("long_signal")).then((pl.col("r_mid") - pl.col("mc")) / PIP),
        ).with_columns(
            exit_signal=~pl.col("in_window") & ~(pl.col("long_signal") | pl.col("short_signal")),
        )
        return apply_news_blackout(out, list(self.currencies), self.blackout_min)


def make() -> TokyoSweep:
    return TokyoSweep()
