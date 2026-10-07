"""073 — "Buy the dip in the trend": 1h RSI(2) pullback with a daily-trend bias, a volatility context and a 15m
confirmation, built for FTMO 1-step (one trade a day, ~15-pip stop = target). EURUSD 2023 + 2024 only.

Variants (layer by layer):  make_a POI only · make_b +bias · make_bp +context (no bias) · make_c +bias +context ·
make_d +bias +context +confirmation · make_dp +bias +confirmation · make_dpp +confirmation only.

See research/runs/073_trend_dip_rsi2/summary.md.
"""

from __future__ import annotations

from datetime import time, timedelta
from pathlib import Path

import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from lib.signals import atr, rsi
from research.regime.news import apply_news_blackout

NY, LONDON = "America/New_York", "Europe/London"
DAILY = Path(__file__).resolve().parents[2] / "data" / "derived" / "eurusd_daily_2023_2024.parquet"


def _bars(base: pl.DataFrame, minutes: int) -> pl.DataFrame:
    return (base.group_by_dynamic("timestamp", every=f"{minutes}m", label="left", closed="left")
            .agg(pl.col("mo").first(), pl.col("mh").max(), pl.col("ml").min(), pl.col("mc").last())
            .with_columns(ct=pl.col("timestamp").dt.offset_by(f"{minutes}m")))


class TrendDipRSI2(Strategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, *, use_bias: bool, use_context: bool, use_confirm: bool, rsi_lo: float = 10.0,
                 rsi_hi: float = 90.0, stop_atr: float = 1.5, currencies: tuple[str, ...] = ("EUR", "USD")) -> None:
        super().__init__(10.0, 10.0, "1m")         # per-trade columns override these
        self.use_bias, self.use_context, self.use_confirm = use_bias, use_context, use_confirm
        self.rsi_lo, self.rsi_hi, self.stop_atr = rsi_lo, rsi_hi, stop_atr
        self.currencies = tuple(currencies)

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        out = df.with_columns(mo=mid("open"), mh=mid("high"), ml=mid("low"), mc=mid("close"))
        base = out.select("timestamp", "mo", "mh", "ml", "mc")

        # 1h: RSI(2), ATR(14) of the last closed bar
        h1 = _bars(base, 60).with_columns(rsi2=rsi(pl.col("mc"), 2),
                                          atr1h=atr(pl.col("mh"), pl.col("ml"), pl.col("mc"), 14)).select("ct", "rsi2", "atr1h")
        out = out.join_asof(h1.drop_nulls(), left_on="close_time", right_on="ct", strategy="backward").drop("ct")
        # 15m: last closed candle's close and the previous candle's high/low
        m15 = _bars(base, 15).with_columns(ph=pl.col("mh").shift(1), pl_=pl.col("ml").shift(1)).select(
            "ct", c15="mc", ph15="ph", pl15="pl_")
        out = out.join_asof(m15.drop_nulls(), left_on="close_time", right_on="ct", strategy="backward").drop("ct")
        # daily (FX day 17:00–17:00 NY): previous completed day's close vs SMA50, ATR14 vs its 100-day median.
        # Precomputed from EURUSD 2023+2024 joined (data/derived/eurusd_daily_2023_2024.parquet) so 2024 has its
        # warm-up from late 2023; values are shifted one FX day (previous completed day only).
        out = out.with_columns(fxday=(pl.col("timestamp").dt.convert_time_zone(NY) + timedelta(hours=7)).dt.date())
        d = pl.read_parquet(DAILY).select("fxday", "trend_prev", "active_prev")
        out = out.join(d, on="fxday", how="left")

        lon = pl.col("close_time").dt.convert_time_zone(LONDON)
        ny = pl.col("close_time").dt.convert_time_zone(NY)
        win = ((lon.dt.time() >= time(8, 0)) & (ny.dt.time() < time(12, 0)) & (ny.dt.weekday() <= 5)
               & (ny.dt.date() == lon.dt.date()))
        long_ = win & (pl.col("rsi2") <= self.rsi_lo)
        short = win & (pl.col("rsi2") >= self.rsi_hi)
        if self.use_bias:
            long_ = long_ & (pl.col("trend_prev") == 1)
            short = short & (pl.col("trend_prev") == -1)
        if self.use_context:
            long_ = long_ & pl.col("active_prev").fill_null(False)
            short = short & pl.col("active_prev").fill_null(False)
        if self.use_confirm:
            long_ = long_ & (pl.col("c15") > pl.col("ph15"))
            short = short & (pl.col("c15") < pl.col("pl15"))
        long_, short = long_.fill_null(False), short.fill_null(False)
        anyx = long_ | short
        nyday = ny.dt.date()
        first = anyx & (anyx.cast(pl.Int32).cum_sum().over(nyday) == 1)           # one trade per NY day
        out = out.with_columns(
            long_signal=first & long_, short_signal=first & short,
            in_window=((lon.dt.time() >= time(8, 0)) & (ny.dt.time() < time(16, 0)) & (ny.dt.weekday() <= 5)).fill_null(False),
        )
        dist = self.stop_atr * pl.col("atr1h") / PIP
        out = out.with_columns(
            sl_pips=pl.when(pl.col("long_signal") | pl.col("short_signal")).then(dist),
            tp_pips=pl.when(pl.col("long_signal") | pl.col("short_signal")).then(dist),
            exit_signal=~pl.col("in_window") & ~(pl.col("long_signal") | pl.col("short_signal")),
        )
        return apply_news_blackout(out, list(self.currencies))


def make_a():   return TrendDipRSI2(use_bias=False, use_context=False, use_confirm=False)   # noqa: E704
def make_b():   return TrendDipRSI2(use_bias=True, use_context=False, use_confirm=False)    # noqa: E704
def make_bp():  return TrendDipRSI2(use_bias=False, use_context=True, use_confirm=False)    # noqa: E704
def make_c():   return TrendDipRSI2(use_bias=True, use_context=True, use_confirm=False)     # noqa: E704
def make_d():   return TrendDipRSI2(use_bias=True, use_context=True, use_confirm=True)      # noqa: E704
def make_dp():  return TrendDipRSI2(use_bias=True, use_context=False, use_confirm=True)     # noqa: E704
def make_dpp(): return TrendDipRSI2(use_bias=False, use_context=False, use_confirm=True)    # noqa: E704
