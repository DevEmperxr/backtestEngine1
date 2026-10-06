"""025 — Idea 2: 1h context + 5m stretch, then a CONFIRMED 5m turn (lower high, then a
close beyond the pullback low); ride the continuation. Stop beyond the lower high.

    make_a(): target = 1h SMA20        make_b(): target = 2 x risk
    make_c(): target = last confirmed 1h swing low (high for longs)

See research/runs/025_turn_confirm_continuation/summary.md.
"""

from __future__ import annotations

from datetime import time

import numpy as np
import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from lib.signals import atr, efficiency_ratio, session_window, sma

NY, LONDON = "America/New_York", "Europe/London"


class TurnConfirmStrategy(Strategy):
    line_columns = ["ma5", "band_up", "band_dn", "ma60"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    force_flat = True
    audit_kind = "turn025"

    def __init__(
        self, *, target: str = "ma60", stretch_atr: float = 1.5, pivot_k: int = 2,
        pivot_k_1h: int = 2, max_bars: int = 36, er_trend: float = 0.32,
        stop_buffer_pips: float = 1.0, timeframe: str = "5m",
    ) -> None:
        super().__init__(10.0, 10.0, timeframe)   # per-trade columns override these
        if target not in ("ma60", "2r", "swing1h"):
            raise ValueError(f"target must be 'ma60', '2r' or 'swing1h', got {target!r}")
        self.target, self.stretch_atr, self.pivot_k = target, stretch_atr, pivot_k
        self.pivot_k_1h, self.max_bars, self.er_trend = pivot_k_1h, max_bars, er_trend
        self.stop_buffer_pips = stop_buffer_pips
        self.window_end, self.window_end_tz = time(16, 0), LONDON

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        out = df.with_columns(mo=mid("open"), mh=mid("high"), ml=mid("low"), mc=mid("close"))
        out = out.with_columns(
            ma5=sma(pl.col("mc"), 20), atr5=atr(pl.col("mh"), pl.col("ml"), pl.col("mc"), 14),
        ).with_columns(
            band_up=pl.col("ma5") + self.stretch_atr * pl.col("atr5"),
            band_dn=pl.col("ma5") - self.stretch_atr * pl.col("atr5"),
            in_window=session_window(pl.col("close_time"), NY, time(7, 0), LONDON, time(16, 0))
                      & (pl.col("close_time").dt.convert_time_zone(NY).dt.weekday() <= 5),
        )
        # 1h context, SMA20 and confirmed 1h swings, from the LAST CLOSED 1h bar
        k1 = self.pivot_k_1h
        w1 = 2 * k1 + 1
        h1 = (out.select("timestamp", "mh", "ml", "mc")
              .group_by_dynamic("timestamp", every="60m", label="left", closed="left")
              .agg(pl.col("mh").max(), pl.col("ml").min(), pl.col("mc").last())
              .with_columns(ct=pl.col("timestamp").dt.offset_by("60m"),
                            er60=efficiency_ratio(pl.col("mc"), 20),
                            ma60=sma(pl.col("mc"), 20),
                            slope60=sma(pl.col("mc"), 20) - sma(pl.col("mc"), 20).shift(5))
              .with_columns(
                  sw1h_lo=pl.when((pl.col("ml") == pl.col("ml").rolling_min(w1, min_samples=w1, center=True)).shift(k1))
                            .then(pl.col("ml").shift(k1)).forward_fill(),
                  sw1h_hi=pl.when((pl.col("mh") == pl.col("mh").rolling_max(w1, min_samples=w1, center=True)).shift(k1))
                            .then(pl.col("mh").shift(k1)).forward_fill())
              .select("ct", "er60", "ma60", "slope60", "sw1h_lo", "sw1h_hi"))
        out = out.join_asof(h1, left_on="close_time", right_on="ct", strategy="backward").drop("ct")
        out = out.with_columns(
            ctx=pl.when((pl.col("er60") >= self.er_trend) & (pl.col("slope60") > 0)).then(pl.lit("up"))
                  .when((pl.col("er60") >= self.er_trend) & (pl.col("slope60") < 0)).then(pl.lit("down"))
                  .when(pl.col("er60").is_not_null()).then(pl.lit("sideways")),
        )

        H, L, C = (out[c].to_numpy() for c in ("mh", "ml", "mc"))
        BU, BD = out["band_up"].to_numpy(), out["band_dn"].to_numpy()
        n, k = len(H), self.pivot_k
        short = np.zeros(n, bool)
        long_ = np.zeros(n, bool)
        sl = np.full(n, np.nan)
        # setup state per side: P (peak), L1 (pullback low), H2 (lower high), as (value, idx)
        S = {"P": None, "L1": None, "H2": None}
        B = {"P": None, "H1": None, "L2": None}      # long mirror: trough, bounce high, higher low
        for t in range(n):
            # 1) break checks use only swings confirmed on EARLIER bars
            if S["P"] is not None and t - S["P"][1] > self.max_bars:
                S = {"P": None, "L1": None, "H2": None}
            if (S["H2"] is not None and t > S["H2"][1] + k and C[t] < S["L1"][0]):
                short[t] = True
                sl[t] = (S["H2"][0] - C[t]) / PIP + self.stop_buffer_pips
                S = {"P": None, "L1": None, "H2": None}
            if B["P"] is not None and t - B["P"][1] > self.max_bars:
                B = {"P": None, "H1": None, "L2": None}
            if (B["L2"] is not None and t > B["L2"][1] + k and C[t] > B["H1"][0]):
                long_[t] = True
                sl[t] = (C[t] - B["L2"][0]) / PIP + self.stop_buffer_pips
                B = {"P": None, "H1": None, "L2": None}
            # 2) register swings confirmed at this bar's close (pivot index t - k)
            i = t - k
            if i - k < 0:
                continue
            is_hi = H[i] == H[i - k:i + k + 1].max()
            is_lo = L[i] == L[i - k:i + k + 1].min()
            if is_lo:
                v = L[i]
                # short side: pullback low (latest low before the lower high)
                if S["P"] is not None and i > S["P"][1] and S["H2"] is None:
                    S["L1"] = (v, i)
                # long side: new trough / higher low
                stretched_dn = not np.isnan(BD[i]) and L[i] <= BD[i]
                if B["P"] is None or v <= B["P"][0]:
                    B = {"P": (v, i), "H1": None, "L2": None} if stretched_dn else {"P": None, "H1": None, "L2": None}
                elif B["H1"] is not None and i > B["H1"][1]:
                    B["L2"] = (v, i)
            if is_hi:
                v = H[i]
                stretched_up = not np.isnan(BU[i]) and H[i] >= BU[i]
                if S["P"] is None or v >= S["P"][0]:
                    S = {"P": (v, i), "L1": None, "H2": None} if stretched_up else {"P": None, "L1": None, "H2": None}
                elif S["L1"] is not None and i > S["L1"][1]:
                    S["H2"] = (v, i)
                # long side: bounce high (latest high before the higher low)
                if B["P"] is not None and i > B["P"][1] and B["L2"] is None:
                    B["H1"] = (v, i)

        out = out.with_columns(
            _s=pl.Series(short), _l=pl.Series(long_), _sl=pl.Series(sl).fill_nan(None),
        )
        if self.target == "ma60":
            tp_s, tp_l = (pl.col("mc") - pl.col("ma60")) / PIP, (pl.col("ma60") - pl.col("mc")) / PIP
        elif self.target == "2r":
            tp_s = tp_l = 2 * pl.col("_sl")
        else:
            tp_s, tp_l = (pl.col("mc") - pl.col("sw1h_lo")) / PIP, (pl.col("sw1h_hi") - pl.col("mc")) / PIP
        s_ok = (pl.col("_s") & pl.col("in_window") & (tp_s > 0)).fill_null(False)
        l_ok = (pl.col("_l") & pl.col("in_window") & (tp_l > 0)).fill_null(False)
        out = out.with_columns(short_signal=s_ok & ~l_ok, long_signal=l_ok & ~s_ok).with_columns(
            sl_pips=pl.when(pl.col("short_signal") | pl.col("long_signal")).then(pl.col("_sl")),
            tp_pips=pl.when(pl.col("short_signal")).then(tp_s).when(pl.col("long_signal")).then(tp_l),
            ctx_class=pl.when(pl.col("short_signal") & (pl.col("ctx") == "up")).then(pl.lit("trend_with"))
                       .when(pl.col("long_signal") & (pl.col("ctx") == "down")).then(pl.lit("trend_with"))
                       .when(pl.col("short_signal") & (pl.col("ctx") == "down")).then(pl.lit("trend_against"))
                       .when(pl.col("long_signal") & (pl.col("ctx") == "up")).then(pl.lit("trend_against"))
                       .when(pl.col("short_signal") | pl.col("long_signal")).then(pl.lit("sideways")),
            exit_signal=~pl.col("in_window"),
        )
        return out.drop("_s", "_l", "_sl")

    @staticmethod
    def report_splits(trades: pl.DataFrame, sig: pl.DataFrame) -> dict[str, pl.DataFrame]:
        t = trades.join(sig.select(pl.col("close_time").alias("entry_time"), "ctx_class"),
                        on="entry_time", how="left")
        return {c: t.filter(pl.col("ctx_class") == c).select(trades.columns)
                for c in ("trend_with", "trend_against", "sideways")}


def make_a() -> TurnConfirmStrategy:
    return TurnConfirmStrategy(target="ma60")


def make_b() -> TurnConfirmStrategy:
    return TurnConfirmStrategy(target="2r")


def make_c() -> TurnConfirmStrategy:
    return TurnConfirmStrategy(target="swing1h")


make = make_a
