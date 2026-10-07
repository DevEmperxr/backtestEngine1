"""075 — gold (XAUUSD): daily-trend bias with (G1) a 1h RSI(2) dip or (G2) a 20-hour breakout, plus a naive
with-trend drift check. Pip-aware (pip 0.1). Rules carried over unchanged from 073-B / 074-P2.

    make_g1()     RSI(2) dip in the daily trend
    make_g2()     20-hour breakout in the daily trend
    make_drift()  enter with the daily trend at the first minute after 08:00 London (reference)

See research/runs/075_gold_trend_bias/summary.md.
"""

from __future__ import annotations

from datetime import time, timedelta
from importlib import import_module
from pathlib import Path

import polars as pl

from lib.data import pip_size
from lib.engine import Strategy
from lib.signals import atr, rsi
from research.regime.news import apply_news_blackout

_073 = import_module("research.strategies.073_trend_dip_rsi2")
NY, LONDON = "America/New_York", "Europe/London"
DAILY = Path(__file__).resolve().parents[2] / "data" / "derived" / "xauusd_daily_2023_2024.parquet"


class GoldTrendBias(Strategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    pip_aware = True
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, *, poi: str, stop_atr: float = 1.5, currencies: tuple[str, ...] = ("XAU", "USD")) -> None:
        super().__init__(10.0, 10.0, "1m")
        if poi not in ("rsi2_dip", "donchian", "drift"):
            raise ValueError(poi)
        self.poi, self.stop_atr, self.currencies = poi, stop_atr, tuple(currencies)
        self.pip = pip_size("XAUUSD")

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        out = df.with_columns(mo=mid("open"), mh=mid("high"), ml=mid("low"), mc=mid("close"))
        base = out.select("timestamp", "mo", "mh", "ml", "mc")
        h1 = (_073._bars(base, 60)
              .with_columns(rsi2=rsi(pl.col("mc"), 2), atr1h=atr(pl.col("mh"), pl.col("ml"), pl.col("mc"), 14),
                            dhi=pl.col("mh").rolling_max(20, min_samples=20), dlo=pl.col("ml").rolling_min(20, min_samples=20))
              .select("ct", "rsi2", "atr1h", "dhi", "dlo"))
        out = out.join_asof(h1.drop_nulls(), left_on="close_time", right_on="ct", strategy="backward").drop("ct")
        out = out.with_columns(fxday=(pl.col("timestamp").dt.convert_time_zone(NY) + timedelta(hours=7)).dt.date())
        out = out.join(pl.read_parquet(DAILY).select("fxday", "trend_prev"), on="fxday", how="left")

        lon = pl.col("close_time").dt.convert_time_zone(LONDON)
        ny = pl.col("close_time").dt.convert_time_zone(NY)
        win = ((lon.dt.time() >= time(8, 0)) & (ny.dt.time() < time(12, 0)) & (ny.dt.weekday() <= 5)
               & (ny.dt.date() == lon.dt.date()) & pl.col("atr1h").is_not_null())   # no signal before the 1h ATR exists
        up, dn = pl.col("trend_prev") == 1, pl.col("trend_prev") == -1
        if self.poi == "rsi2_dip":
            long_, short = up & (pl.col("rsi2") <= 10), dn & (pl.col("rsi2") >= 90)
        elif self.poi == "donchian":
            long_, short = up & (pl.col("mc") > pl.col("dhi")), dn & (pl.col("mc") < pl.col("dlo"))
        else:
            long_, short = up, dn
        long_, short = (win & long_).fill_null(False), (win & short).fill_null(False)
        anyx = long_ | short
        first = anyx & (anyx.cast(pl.Int32).cum_sum().over(ny.dt.date()) == 1)
        out = out.with_columns(
            long_signal=first & long_, short_signal=first & short,
            in_window=((lon.dt.time() >= time(8, 0)) & (ny.dt.time() < time(16, 0)) & (ny.dt.weekday() <= 5)).fill_null(False),
        )
        dist = self.stop_atr * pl.col("atr1h") / self.pip
        sig = pl.col("long_signal") | pl.col("short_signal")
        out = out.with_columns(sl_pips=pl.when(sig).then(dist), tp_pips=pl.when(sig).then(dist),
                               exit_signal=~pl.col("in_window") & ~sig)
        return apply_news_blackout(out, list(self.currencies))


def make_g1():    return GoldTrendBias(poi="rsi2_dip")   # noqa: E704
def make_g2():    return GoldTrendBias(poi="donchian")   # noqa: E704
def make_drift(): return GoldTrendBias(poi="drift")      # noqa: E704
