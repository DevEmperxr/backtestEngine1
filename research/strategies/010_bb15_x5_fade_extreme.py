"""010 — 15m Bollinger(20, 2) stretch, confirmed by a 5m SMA 9/21 cross back
toward the mean within 60 min; TP = 80% of the way to the 15m middle band;
SL beyond the setup extreme + 2 pips. Window 07:00 NY -> 16:00 London.

011 reuses this class with stop_mode="atr". See
research/runs/010_bb15_x5_fade_extreme/summary.md.
"""

from __future__ import annotations

from datetime import time

import numpy as np
import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from lib.signals import atr, crossover, higher_tf_join, session_window, sma

NY, LONDON = "America/New_York", "Europe/London"


class Bb15Cross5FadeStrategy(Strategy):
    line_columns = ["bb_mid15", "bb_up15", "bb_lo15", "sma_fast", "sma_slow"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    force_flat = True
    audit_kind = "bb15x5"

    def __init__(
        self, *, bb_tf: str = "15m", bb_n: int = 20, bb_k: float = 2.0,
        fast_n: int = 9, slow_n: int = 21, setup_life_min: int = 60,
        tp_frac: float = 0.8, stop_mode: str = "extreme", stop_buffer_pips: float = 2.0,
        atr_n: int = 14, atr_sl_mult: float = 2.5, timeframe: str = "5m",
    ) -> None:
        super().__init__(10.0, 10.0, timeframe)   # per-trade columns override these
        if stop_mode not in ("extreme", "atr"):
            raise ValueError(f"stop_mode must be 'extreme' or 'atr', got {stop_mode!r}")
        self.bb_tf, self.bb_n, self.bb_k = bb_tf, bb_n, bb_k
        self.fast_n, self.slow_n = fast_n, slow_n
        self.setup_life_min, self.tp_frac = setup_life_min, tp_frac
        self.stop_mode, self.stop_buffer_pips = stop_mode, stop_buffer_pips
        self.atr_n, self.atr_sl_mult = atr_n, atr_sl_mult
        self.window_end, self.window_end_tz = time(16, 0), LONDON

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        c15 = pl.col("close")
        out = df.with_columns(
            mid_close=mid("close"), mid_high=mid("high"), mid_low=mid("low"),
            in_window=session_window(pl.col("close_time"), NY, time(7, 0), LONDON, time(16, 0))
                      & (pl.col("close_time").dt.convert_time_zone(NY).dt.weekday() <= 5),
        )
        # 15m band values of the LAST CLOSED 15m bar (as-of on close_time)
        sd = c15.rolling_std(self.bb_n, min_samples=self.bb_n)
        out = higher_tf_join(out, self.bb_tf, "mid_close", {
            "bb_mid15": sma(c15, self.bb_n),
            "close15": c15,
            "bar15_close_time": pl.col("timestamp").dt.offset_by(self.bb_tf),
            "_sd15": sd,
        }).with_columns(
            bb_up15=pl.col("bb_mid15") + self.bb_k * pl.col("_sd15"),
            bb_lo15=pl.col("bb_mid15") - self.bb_k * pl.col("_sd15"),
        )
        life = pl.duration(minutes=self.setup_life_min)
        out = out.with_columns(
            # most recent qualifying 15m close (refreshes on each new one)
            setup_long_t=pl.when(pl.col("close15") < pl.col("bb_lo15"))
                          .then(pl.col("bar15_close_time")).forward_fill(),
            setup_short_t=pl.when(pl.col("close15") > pl.col("bb_up15"))
                           .then(pl.col("bar15_close_time")).forward_fill(),
            # most recent 5m bar that reached the (current) 15m middle band
            touch_mid_up_t=pl.when(pl.col("mid_high") >= pl.col("bb_mid15"))
                            .then(pl.col("close_time")).forward_fill(),
            touch_mid_dn_t=pl.when(pl.col("mid_low") <= pl.col("bb_mid15"))
                            .then(pl.col("close_time")).forward_fill(),
            sma_fast=sma(pl.col("mid_close"), self.fast_n),
            sma_slow=sma(pl.col("mid_close"), self.slow_n),
        )
        cross_up, cross_down = crossover(pl.col("sma_fast"), pl.col("sma_slow"))
        active_long = (
            (pl.col("close_time") - pl.col("setup_long_t") <= life)
            & (pl.col("touch_mid_up_t").is_null() | (pl.col("touch_mid_up_t") <= pl.col("setup_long_t")))
        )
        active_short = (
            (pl.col("close_time") - pl.col("setup_short_t") <= life)
            & (pl.col("touch_mid_dn_t").is_null() | (pl.col("touch_mid_dn_t") <= pl.col("setup_short_t")))
        )
        out = out.with_columns(
            long_signal=(cross_up & active_long & (pl.col("mid_close") < pl.col("bb_mid15"))
                         & pl.col("in_window")).fill_null(False),
            short_signal=(cross_down & active_short & (pl.col("mid_close") > pl.col("bb_mid15"))
                          & pl.col("in_window")).fill_null(False),
            atr_pips=atr(pl.col("mid_high"), pl.col("mid_low"), pl.col("mid_close"), self.atr_n) / PIP,
        ).with_columns(
            tp_pips=pl.when(pl.col("long_signal") | pl.col("short_signal"))
                     .then(self.tp_frac * (pl.col("mid_close") - pl.col("bb_mid15")).abs() / PIP),
            exit_signal=~pl.col("in_window"),
        )
        return out.with_columns(sl_pips=self._stops(out)).drop("_sd15")

    def _stops(self, out: pl.DataFrame) -> pl.Series:
        long_ = out["long_signal"].to_numpy()
        short_ = out["short_signal"].to_numpy()
        sl = np.full(out.height, np.nan)
        if self.stop_mode == "atr":
            a = out["atr_pips"].to_numpy()
            m = long_ | short_
            sl[m] = a[m] * self.atr_sl_mult
            return pl.Series("sl_pips", sl).fill_nan(None)
        # extreme since the start of the setup 15m bar, through the signal bar
        # (rows <= i only — no lookahead)
        ts = out["timestamp"].dt.epoch("ns").to_numpy()
        lo, hi, cl = (out[c].to_numpy() for c in ("mid_low", "mid_high", "mid_close"))
        s_long = out["setup_long_t"].dt.epoch("ns").to_numpy()
        s_short = out["setup_short_t"].dt.epoch("ns").to_numpy()
        tf15 = 15 * 60 * 1_000_000_000 if self.bb_tf == "15m" else None
        if tf15 is None:
            raise ValueError("extreme stop assumes a 15m setup bar")
        buf = self.stop_buffer_pips * PIP
        for i in np.flatnonzero(long_ | short_):
            start = np.searchsorted(ts, (s_long[i] if long_[i] else s_short[i]) - tf15, side="left")
            if long_[i]:
                sl[i] = (cl[i] - (lo[start:i + 1].min() - buf)) / PIP
            else:
                sl[i] = ((hi[start:i + 1].max() + buf) - cl[i]) / PIP
        return pl.Series("sl_pips", sl).fill_nan(None)


def make() -> Bb15Cross5FadeStrategy:
    return Bb15Cross5FadeStrategy(bb_tf="15m", bb_n=20, bb_k=2.0, fast_n=9, slow_n=21,
                                  setup_life_min=120, tp_frac=0.8, stop_mode="extreme",
                                  stop_buffer_pips=2.0)
