"""022 — Idea 1: in a 1h trend, fade a stretched 5m move at a 1m liquidity sweep;
target the 5m SMA20; stop 1 pip beyond the sweep. Window 07:00 NY -> 16:00 London.

    make():          sweep entry
    make_control():  no sweep: enter at the first 1m bar that reaches the 2 x ATR stretch

See research/runs/022_sweep_fade_to_ma/summary.md.
"""

from __future__ import annotations

from datetime import time

import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from lib.signals import atr, efficiency_ratio, session_window, sma

NY, LONDON = "America/New_York", "Europe/London"


def _htf(m: pl.DataFrame, minutes: int) -> pl.DataFrame:
    """Mid OHLC bars of `minutes` built from the 1m mid bars, with close_time."""
    return (m.group_by_dynamic("timestamp", every=f"{minutes}m", label="left", closed="left")
            .agg(pl.col("mo").first(), pl.col("mh").max(), pl.col("ml").min(), pl.col("mc").last())
            .with_columns(ct=pl.col("timestamp").dt.offset_by(f"{minutes}m")))


class SweepFadeStrategy(Strategy):
    line_columns = ["ma5", "band_up", "band_dn", "swing_hi", "swing_lo"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    force_flat = True
    audit_kind = "sweep022"

    def __init__(
        self, *, mode: str = "sweep", stretch_atr: float = 2.0, pivot_k: int = 3,
        er_trend: float = 0.32, stop_buffer_pips: float = 1.0, timeframe: str = "1m",
    ) -> None:
        super().__init__(10.0, 10.0, timeframe)   # per-trade columns override these
        if mode not in ("sweep", "control"):
            raise ValueError(f"mode must be 'sweep' or 'control', got {mode!r}")
        self.mode, self.stretch_atr, self.pivot_k = mode, stretch_atr, pivot_k
        self.er_trend, self.stop_buffer_pips = er_trend, stop_buffer_pips
        self.window_end, self.window_end_tz = time(16, 0), LONDON

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        out = df.with_columns(mo=mid("open"), mh=mid("high"), ml=mid("low"), mc=mid("close"))
        base = out.select("timestamp", "mo", "mh", "ml", "mc")

        # 5m SMA20 / ATR14 of the LAST CLOSED 5m bar
        b5 = _htf(base, 5).with_columns(
            ma5=sma(pl.col("mc"), 20), atr5=atr(pl.col("mh"), pl.col("ml"), pl.col("mc"), 14),
        ).select("ct", "ma5", "atr5")
        out = out.join_asof(b5, left_on="close_time", right_on="ct", strategy="backward").drop("ct")

        # 1h context of the LAST CLOSED 1h bar
        b60 = _htf(base, 60).with_columns(
            er60=efficiency_ratio(pl.col("mc"), 20),
            slope60=sma(pl.col("mc"), 20) - sma(pl.col("mc"), 20).shift(5),
        ).select("ct", "er60", "slope60")
        out = out.join_asof(b60, left_on="close_time", right_on="ct", strategy="backward").drop("ct")
        out = out.with_columns(
            ctx=pl.when((pl.col("er60") >= self.er_trend) & (pl.col("slope60") > 0)).then(pl.lit("up"))
                  .when((pl.col("er60") >= self.er_trend) & (pl.col("slope60") < 0)).then(pl.lit("down"))
                  .when(pl.col("er60").is_not_null()).then(pl.lit("sideways")),
        )

        # 1m swings: highest/lowest of the 2k+1 bars centred on it, usable only once
        # confirmed (k bars later) and only from the NEXT bar on.
        k = self.pivot_k
        w = 2 * k + 1
        is_ph = pl.col("mh") == pl.col("mh").rolling_max(w, min_samples=w, center=True)
        is_pl = pl.col("ml") == pl.col("ml").rolling_min(w, min_samples=w, center=True)
        out = out.with_columns(
            swing_hi=pl.when(is_ph.shift(k)).then(pl.col("mh").shift(k)).forward_fill().shift(1),
            swing_lo=pl.when(is_pl.shift(k)).then(pl.col("ml").shift(k)).forward_fill().shift(1),
            band_up=pl.col("ma5") + self.stretch_atr * pl.col("atr5"),
            band_dn=pl.col("ma5") - self.stretch_atr * pl.col("atr5"),
            in_window=session_window(pl.col("close_time"), NY, time(7, 0), LONDON, time(16, 0))
                      & (pl.col("close_time").dt.convert_time_zone(NY).dt.weekday() <= 5),
        )
        up = (pl.col("mh") >= pl.col("band_up")).fill_null(False)
        dn = (pl.col("ml") <= pl.col("band_dn")).fill_null(False)
        if self.mode == "sweep":
            short = up & (pl.col("mh") > pl.col("swing_hi")) & (pl.col("mc") < pl.col("swing_hi"))
            long_ = dn & (pl.col("ml") < pl.col("swing_lo")) & (pl.col("mc") > pl.col("swing_lo"))
        else:   # control: first bar of each stretch episode
            short = up & ~up.shift(1, fill_value=False)
            long_ = dn & ~dn.shift(1, fill_value=False)
        tp_s = (pl.col("mc") - pl.col("ma5")) / PIP
        tp_l = (pl.col("ma5") - pl.col("mc")) / PIP
        short = (short & pl.col("in_window") & (tp_s > 0)).fill_null(False)
        long_ = (long_ & pl.col("in_window") & (tp_l > 0)).fill_null(False)
        buf = self.stop_buffer_pips
        out = out.with_columns(
            short_signal=short & ~long_, long_signal=long_ & ~short,
        ).with_columns(
            sl_pips=pl.when(pl.col("short_signal")).then((pl.col("mh") - pl.col("mc")) / PIP + buf)
                     .when(pl.col("long_signal")).then((pl.col("mc") - pl.col("ml")) / PIP + buf),
            tp_pips=pl.when(pl.col("short_signal")).then(tp_s).when(pl.col("long_signal")).then(tp_l),
            ctx_class=pl.when(pl.col("short_signal") & (pl.col("ctx") == "up")).then(pl.lit("trend_with"))
                       .when(pl.col("long_signal") & (pl.col("ctx") == "down")).then(pl.lit("trend_with"))
                       .when(pl.col("short_signal") & (pl.col("ctx") == "down")).then(pl.lit("trend_against"))
                       .when(pl.col("long_signal") & (pl.col("ctx") == "up")).then(pl.lit("trend_against"))
                       .when(pl.col("short_signal") | pl.col("long_signal")).then(pl.lit("sideways")),
            exit_signal=~pl.col("in_window"),
        )
        return out

    @staticmethod
    def report_splits(trades: pl.DataFrame, sig: pl.DataFrame) -> dict[str, pl.DataFrame]:
        """Pre-registered: trending-with (primary), trending-against, sideways."""
        t = trades.join(sig.select(pl.col("close_time").alias("entry_time"), "ctx_class"),
                        on="entry_time", how="left")
        cols = trades.columns
        return {c: t.filter(pl.col("ctx_class") == c).select(cols)
                for c in ("trend_with", "trend_against", "sideways")}


def make() -> SweepFadeStrategy:
    return SweepFadeStrategy(mode="sweep", stretch_atr=2.0, pivot_k=3, er_trend=0.32, stop_buffer_pips=1.0)


def make_control() -> SweepFadeStrategy:
    return SweepFadeStrategy(mode="control", stretch_atr=2.0, pivot_k=3, er_trend=0.32, stop_buffer_pips=1.0)
