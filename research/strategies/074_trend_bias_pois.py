"""074 — daily-trend bias (from 073) with three pre-declared POIs and immediate entry, FTMO 1-step shape, EURUSD.

    make_p1()  pullback to the 1h SMA20 in the trend's direction
    make_p2()  break of the 20-hour (Donchian) extreme in the trend's direction
    make_p3()  break of the previous FX day's high/low in the trend's direction

Execution: next 1m open; stop = target = 1.5 x ATR(14) of the last closed 1h bar; one trade per NY day; signals
08:00 London -> 12:00 NY; flat 16:00 NY; FTMO ±2 min news. See research/runs/074_trend_bias_pois/summary.md.
"""

from __future__ import annotations

from datetime import time, timedelta
from importlib import import_module

import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from lib.signals import atr, sma
from research.regime.news import apply_news_blackout

_073 = import_module("research.strategies.073_trend_dip_rsi2")
NY, LONDON = "America/New_York", "Europe/London"


class TrendBiasPOI(Strategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, *, poi: str, stop_atr: float = 1.5, currencies: tuple[str, ...] = ("EUR", "USD")) -> None:
        super().__init__(10.0, 10.0, "1m")
        if poi not in ("sma_pullback", "donchian", "prev_day"):
            raise ValueError(poi)
        self.poi, self.stop_atr, self.currencies = poi, stop_atr, tuple(currencies)

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        out = df.with_columns(mo=mid("open"), mh=mid("high"), ml=mid("low"), mc=mid("close"))
        base = out.select("timestamp", "mo", "mh", "ml", "mc")
        h1 = (_073._bars(base, 60)
              .with_columns(sma20=sma(pl.col("mc"), 20), atr1h=atr(pl.col("mh"), pl.col("ml"), pl.col("mc"), 14),
                            dhi=pl.col("mh").rolling_max(20, min_samples=20), dlo=pl.col("ml").rolling_min(20, min_samples=20))
              .select("ct", c1h="mc", sma20="sma20", atr1h="atr1h", dhi="dhi", dlo="dlo"))
        out = out.join_asof(h1.drop_nulls(), left_on="close_time", right_on="ct", strategy="backward").drop("ct")
        out = out.with_columns(fxday=(pl.col("timestamp").dt.convert_time_zone(NY) + timedelta(hours=7)).dt.date())
        d = (pl.read_parquet(_073.DAILY).sort("fxday")
             .with_columns(pdh=pl.col("dh").shift(1), pdl=pl.col("dl").shift(1))
             .select("fxday", "trend_prev", "pdh", "pdl"))
        out = out.join(d, on="fxday", how="left")

        lon = pl.col("close_time").dt.convert_time_zone(LONDON)
        ny = pl.col("close_time").dt.convert_time_zone(NY)
        win = ((lon.dt.time() >= time(8, 0)) & (ny.dt.time() < time(12, 0)) & (ny.dt.weekday() <= 5)
               & (ny.dt.date() == lon.dt.date()))
        up, dn = pl.col("trend_prev") == 1, pl.col("trend_prev") == -1
        if self.poi == "sma_pullback":
            long_ = up & (pl.col("c1h") > pl.col("sma20")) & (pl.col("ml") <= pl.col("sma20"))
            short = dn & (pl.col("c1h") < pl.col("sma20")) & (pl.col("mh") >= pl.col("sma20"))
        elif self.poi == "donchian":
            long_ = up & (pl.col("mc") > pl.col("dhi"))
            short = dn & (pl.col("mc") < pl.col("dlo"))
        else:
            long_ = up & (pl.col("mc") > pl.col("pdh"))
            short = dn & (pl.col("mc") < pl.col("pdl"))
        long_, short = (win & long_).fill_null(False), (win & short).fill_null(False)
        anyx = long_ | short
        first = anyx & (anyx.cast(pl.Int32).cum_sum().over(ny.dt.date()) == 1)
        out = out.with_columns(
            long_signal=first & long_, short_signal=first & short,
            in_window=((lon.dt.time() >= time(8, 0)) & (ny.dt.time() < time(16, 0)) & (ny.dt.weekday() <= 5)).fill_null(False),
        )
        dist = self.stop_atr * pl.col("atr1h") / PIP
        sig = pl.col("long_signal") | pl.col("short_signal")
        out = out.with_columns(sl_pips=pl.when(sig).then(dist), tp_pips=pl.when(sig).then(dist),
                               exit_signal=~pl.col("in_window") & ~sig)
        return apply_news_blackout(out, list(self.currencies))


def make_p1(): return TrendBiasPOI(poi="sma_pullback")   # noqa: E704
def make_p2(): return TrendBiasPOI(poi="donchian")       # noqa: E704
def make_p3(): return TrendBiasPOI(poi="prev_day")       # noqa: E704
