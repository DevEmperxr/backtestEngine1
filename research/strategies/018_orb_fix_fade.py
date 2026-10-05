"""018 — Fade the day's 005 opening-range breakout at the 16:00 London fix if
that breakout trade is still open; TP at the breakout's SL level, SL at its TP
level, flat at 16:00 New York.

See research/runs/018_orb_fix_fade/summary.md.
"""

from __future__ import annotations

from datetime import time
from importlib import import_module

import numpy as np
import polars as pl

from lib.data import PIP
from lib.engine import Strategy, _sl_tp_levels
from lib.signals import atr, session_window

_orb = import_module("research.strategies.005_orb_ny_prenews")
NY, LONDON = _orb.NY, "Europe/London"


class OrbFixFadeStrategy(Strategy):
    line_columns = ["mid_close"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    force_flat = True
    audit_kind = "orb_fix_fade"

    def __init__(
        self, *, fix_time: time = time(16, 0), timeframe: str = "1m",
        exit_mode: str = "mirror", atr_tf: str = "1h", atr_n: int = 14,
        sl_atr: float = 1.5, tp_atr: float = 1.5,
    ) -> None:
        super().__init__(10.0, 10.0, timeframe)   # per-trade columns override these
        if exit_mode not in ("mirror", "time", "atr", "range"):
            raise ValueError(f"unknown exit_mode {exit_mode!r}")
        self.fix_time = fix_time
        # mirror = 018 (TP at breakout SL, SL at breakout TP); time = 019A;
        # atr = 019B; range = 019C. See research/runs/019_orb_fix_fade_exits.
        self.exit_mode, self.atr_tf, self.atr_n = exit_mode, atr_tf, atr_n
        self.sl_atr, self.tp_atr = sl_atr, tp_atr
        self.window_end, self.window_end_tz = time(16, 0), NY
        self.orb = _orb.make()                     # 005, unchanged

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        orb = self.orb.generate_signals(df)
        close_l = pl.col("close_time").dt.convert_time_zone(LONDON)
        out = df.with_columns(
            mid_close=(pl.col("bid_close") + pl.col("ask_close")) / 2,
            in_window=session_window(pl.col("close_time"), LONDON, self.fix_time, NY, time(16, 0))
                      & (close_l.dt.weekday() <= 5),
            is_fix=(close_l.dt.time() == self.fix_time) & (close_l.dt.weekday() <= 5),
        )
        if self.exit_mode != "mirror":
            # ATR of the LAST CLOSED higher-tf mid bar (as-of backward on close_time)
            m = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
            htf = (
                df.select("timestamp", h=m("high"), l=m("low"), c=m("close"))
                .group_by_dynamic("timestamp", every=self.atr_tf, label="left", closed="left")
                .agg(pl.col("h").max(), pl.col("l").min(), pl.col("c").last())
                .with_columns(_atr_ct=pl.col("timestamp").dt.offset_by(self.atr_tf),
                              atr_pips=atr(pl.col("h"), pl.col("l"), pl.col("c"), self.atr_n) / PIP)
                .select("_atr_ct", "atr_pips")
            )
            out = out.join_asof(htf, left_on="close_time", right_on="_atr_ct",
                                strategy="backward").drop("_atr_ct")
        n = out.height
        is_fix = out["is_fix"].to_numpy()
        fix_idx = np.flatnonzero(is_fix)
        bl, bh = df["bid_low"].to_numpy(), df["bid_high"].to_numpy()
        al, ah = df["ask_low"].to_numpy(), df["ask_high"].to_numpy()
        ao, bo = df["ask_open"].to_numpy(), df["bid_open"].to_numpy()
        mid = out["mid_close"].to_numpy()
        o_long, o_short = orb["long_signal"].to_numpy(), orb["short_signal"].to_numpy()
        o_sl, o_tp = orb["sl_pips"].to_numpy(), orb["tp_pips"].to_numpy()
        r_hi, r_lo = orb["range_hi_d"].to_numpy(), orb["range_lo_d"].to_numpy()
        a = out["atr_pips"].to_numpy() if self.exit_mode != "mirror" else None

        long_sig = np.zeros(n, bool)
        short_sig = np.zeros(n, bool)
        sl = np.full(n, np.nan)
        tp = np.full(n, np.nan)
        for i in np.flatnonzero(o_long | o_short):
            e = i + 1                                     # breakout entry bar (t+1)
            k = np.searchsorted(fix_idx, e)               # first fix bar at/after entry
            if e >= n or k >= len(fix_idx):
                continue
            f = fix_idx[k]
            d = 1 if o_long[i] else -1
            entry = ao[e] if d == 1 else bo[e]
            b_sl, b_tp = _sl_tp_levels(d, entry, o_sl[i], o_tp[i])
            # bars e..f only (all closed by 16:00 London): was either level touched?
            if d == 1:      # long exits against the bid
                touched = (bl[e:f + 1] <= b_sl).any() or (bh[e:f + 1] >= b_tp).any()
            else:           # short exits against the ask
                touched = (ah[e:f + 1] >= b_sl).any() or (al[e:f + 1] <= b_tp).any()
            if touched:
                continue
            right_side = (b_sl > mid[f] > b_tp) if d == -1 else (b_sl < mid[f] < b_tp)
            if not right_side:
                continue
            if self.exit_mode == "mirror":
                # fade: opposite direction; TP at the breakout's SL, SL at its TP
                fade_tp = abs(b_sl - mid[f]) / PIP
                fade_sl = abs(mid[f] - b_tp) / PIP
            else:
                atr_f = a[f]
                if not (atr_f == atr_f) or atr_f <= 0:          # null/NaN ATR: no trade
                    continue
                if self.exit_mode == "time":
                    fade_sl, fade_tp = 3.0 * atr_f, 10.0 * atr_f
                elif self.exit_mode == "atr":
                    fade_sl, fade_tp = self.sl_atr * atr_f, self.tp_atr * atr_f
                else:  # range: back to the edge the breakout broke
                    edge = r_hi[i] if d == 1 else r_lo[i]
                    fade_tp = ((mid[f] - edge) if d == 1 else (edge - mid[f])) / PIP
                    fade_sl = self.sl_atr * atr_f
            if fade_tp <= 0 or fade_sl <= 0:
                continue
            if d == 1:
                short_sig[f] = True
            else:
                long_sig[f] = True
            sl[f], tp[f] = fade_sl, fade_tp
        return out.with_columns(
            long_signal=pl.Series(long_sig) & pl.col("in_window"),
            short_signal=pl.Series(short_sig) & pl.col("in_window"),
            sl_pips=pl.Series(sl).fill_nan(None),
            tp_pips=pl.Series(tp).fill_nan(None),
            exit_signal=~pl.col("in_window"),
        )


def make() -> OrbFixFadeStrategy:
    return OrbFixFadeStrategy(fix_time=time(16, 0))
