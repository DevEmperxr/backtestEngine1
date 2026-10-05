"""009 — Bollinger(20, 2) + RSI(14) 30/70 stretch fade on 5m, inside
07:00 NY -> 16:00 London; TP = back to the middle band, SL = 2.5 x ATR(14).

See research/runs/009_band_rsi_fade/summary.md.
"""

from __future__ import annotations

from datetime import time

import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from lib.signals import atr, rsi, session_window, sma

NY, LONDON = "America/New_York", "Europe/London"


class BandRsiFadeStrategy(Strategy):
    line_columns = ["bb_mid", "bb_up", "bb_lo"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    force_flat = True
    audit_kind = "band_rsi"

    def __init__(
        self, *, bb_n: int = 20, bb_k: float = 2.0, rsi_n: int = 14, rsi_lo: float = 30,
        rsi_hi: float = 70, atr_n: int = 14, atr_sl_mult: float = 2.5, timeframe: str = "5m",
    ) -> None:
        super().__init__(10.0, 10.0, timeframe)   # per-trade columns override these
        self.bb_n, self.bb_k = bb_n, bb_k
        self.rsi_n, self.rsi_lo, self.rsi_hi = rsi_n, rsi_lo, rsi_hi
        self.atr_n, self.atr_sl_mult = atr_n, atr_sl_mult
        self.window_end, self.window_end_tz = time(16, 0), LONDON

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        c = pl.col("mid_close")
        out = df.with_columns(
            mid_close=mid("close"),
            in_window=session_window(pl.col("close_time"), NY, time(7, 0), LONDON, time(16, 0))
                      & (pl.col("close_time").dt.convert_time_zone(NY).dt.weekday() <= 5),
        ).with_columns(
            bb_mid=sma(c, self.bb_n),
            bb_sd=c.rolling_std(self.bb_n, min_samples=self.bb_n),
            rsi=rsi(c, self.rsi_n),
            atr_pips=atr(mid("high"), mid("low"), c, self.atr_n) / PIP,
        ).with_columns(
            bb_up=pl.col("bb_mid") + self.bb_k * pl.col("bb_sd"),
            bb_lo=pl.col("bb_mid") - self.bb_k * pl.col("bb_sd"),
        ).with_columns(
            long_signal=((c < pl.col("bb_lo")) & (pl.col("rsi") < self.rsi_lo)
                         & pl.col("in_window")).fill_null(False),
            short_signal=((c > pl.col("bb_up")) & (pl.col("rsi") > self.rsi_hi)
                          & pl.col("in_window")).fill_null(False),
        ).with_columns(
            tp_pips=pl.when(pl.col("long_signal") | pl.col("short_signal"))
                     .then((c - pl.col("bb_mid")).abs() / PIP),
            sl_pips=pl.when(pl.col("long_signal") | pl.col("short_signal"))
                     .then(pl.col("atr_pips") * self.atr_sl_mult),
            exit_signal=~pl.col("in_window"),
        )
        return out


def make() -> BandRsiFadeStrategy:
    return BandRsiFadeStrategy(bb_n=20, bb_k=2.0, rsi_n=14, rsi_lo=30, rsi_hi=70,
                               atr_n=14, atr_sl_mult=2.5)
